"""Train the dropout-risk model on OULAD and write the runtime artifact plus an evaluation report.

Run from backend/:  uv run python ml/train_risk.py

Question answered: given a student's activity and scores up to day t, what is the probability they
withdraw from the module in the next 28 days? Rows are (student, module presentation, landmark day t),
landmarks weekly from day 21 after the student's first activity. Students are split into train /
calibration / test groups so no student appears on both sides of any split.
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml.risk_features import FEATURES, HORIZON_DAYS, MIN_HISTORY_DAYS, MODEL_FEATURES, build_features  # noqa: E402

MODEL_COLS = [FEATURES.index(f) for f in MODEL_FEATURES]

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "oulad"
ARTIFACT = HERE.parent / "app" / "ml" / "artifacts" / "risk_v1.json"
REPORT = HERE / "reports" / "risk_oulad.json"
SEED = 0
KEY = ["code_module", "code_presentation", "id_student"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_entities() -> pd.DataFrame:
    na = ["?"]
    info = pd.read_csv(DATA / "studentInfo.csv", na_values=na, usecols=KEY + ["final_result"])
    reg = pd.read_csv(DATA / "studentRegistration.csv", na_values=na, usecols=KEY + ["date_unregistration"])
    courses = pd.read_csv(DATA / "courses.csv")
    ent = info.merge(reg, on=KEY, how="inner").merge(courses, on=["code_module", "code_presentation"])
    ent["withdrew"] = ent["date_unregistration"].notna()
    # Labelled "Withdrawn" but no withdrawal date: timing unknown, so the row cannot be labelled.
    unknown = (ent["final_result"] == "Withdrawn") & ~ent["withdrew"]
    log(f"entities: {len(ent)}, withdrew with a date: {int(ent['withdrew'].sum())}, "
        f"withdrawn with unknown date (dropped): {int(unknown.sum())}")
    ent = ent[~unknown].reset_index(drop=True)
    ent["eid"] = np.arange(len(ent))
    return ent


def load_daily_activity(ent: pd.DataFrame) -> pd.DataFrame:
    log("reading studentVle.csv (about 450 MB)")
    vle = pd.read_csv(
        DATA / "studentVle.csv",
        usecols=KEY + ["date", "sum_click"],
        dtype={"code_module": "category", "code_presentation": "category", "id_student": "int32",
               "date": "int16", "sum_click": "int32"},
    )
    vle = vle.groupby(KEY + ["date"], observed=True, as_index=False)["sum_click"].sum()
    for col in ("code_module", "code_presentation"):
        vle[col] = vle[col].astype(str)
    vle = vle.merge(ent[KEY + ["eid"]], on=KEY, how="inner")
    return vle.sort_values(["eid", "date"]).reset_index(drop=True)


def load_scores(ent: pd.DataFrame) -> pd.DataFrame:
    sa = pd.read_csv(DATA / "studentAssessment.csv", na_values=["?"])
    assess = pd.read_csv(DATA / "assessments.csv", usecols=["id_assessment", "code_module", "code_presentation"])
    sa = sa.merge(assess, on="id_assessment").merge(ent[KEY + ["eid"]], on=KEY, how="inner")
    sa = sa.dropna(subset=["score", "date_submitted"])
    sa["fraction"] = sa["score"].clip(0, 100) / 100.0
    return sa.sort_values(["eid", "date_submitted"]).reset_index(drop=True)


def build_dataset(ent, vle, sa):
    log("building landmark rows")
    vle_idx = {e: i for e, i in zip(*np.unique(vle["eid"].to_numpy(), return_index=True))}
    vle_end = np.append(list(vle_idx.values())[1:], len(vle))
    vle_bounds = dict(zip(vle_idx.keys(), zip(vle_idx.values(), vle_end)))
    sa_idx = {e: i for e, i in zip(*np.unique(sa["eid"].to_numpy(), return_index=True))}
    sa_end = np.append(list(sa_idx.values())[1:], len(sa))
    sa_bounds = dict(zip(sa_idx.keys(), zip(sa_idx.values(), sa_end)))

    vdate, vclick = vle["date"].to_numpy(), vle["sum_click"].to_numpy()
    sdate, sfrac = sa["date_submitted"].to_numpy(), sa["fraction"].to_numpy()

    X, y, student, presentation, week = [], [], [], [], []
    for r in ent.itertuples(index=False):
        if r.eid not in vle_bounds:
            continue  # no recorded activity: nothing to predict from
        lo, hi = vle_bounds[r.eid]
        dates, clicks = vdate[lo:hi], vclick[lo:hi]
        origin = int(dates.min())
        length = int(r.module_presentation_length)
        n_days = length - origin + 1
        keep = (dates - origin) < n_days
        daily = np.zeros(n_days)
        daily[dates[keep] - origin] = clicks[keep]

        unreg = r.date_unregistration if r.withdrew else np.inf
        # Landmark day t (absolute day = origin + t): still registered, and a full horizon fits in the module.
        t_max = length - HORIZON_DAYS - origin
        if r.withdrew:
            t_max = min(t_max, int(unreg) - 1 - origin)
        landmarks = np.arange(MIN_HISTORY_DAYS, t_max + 1, 7)
        if landmarks.size == 0:
            continue

        scores = []
        if r.eid in sa_bounds:
            s_lo, s_hi = sa_bounds[r.eid]
            scores = [(int(d) - origin, float(f)) for d, f in zip(sdate[s_lo:s_hi], sfrac[s_lo:s_hi])]

        absolute = origin + landmarks
        label = ((unreg > absolute) & (unreg <= absolute + HORIZON_DAYS)).astype(int)
        X.append(build_features(daily, scores, landmarks))
        y.append(label)
        student.append(np.full(len(landmarks), r.id_student))
        presentation.append(np.full(len(landmarks), r.code_presentation))
        week.append(landmarks // 7)
    return (np.vstack(X), np.concatenate(y), np.concatenate(student),
            np.concatenate(presentation), np.concatenate(week))


def split_students(students: np.ndarray, rng) -> dict[str, np.ndarray]:
    unique = rng.permutation(np.unique(students))
    n = len(unique)
    parts = {"train": unique[: int(0.6 * n)], "calib": unique[int(0.6 * n): int(0.8 * n)], "test": unique[int(0.8 * n):]}
    return {k: np.isin(students, v) for k, v in parts.items()}


def ece(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    edges[-1] += 1e-12
    total, err = len(y), 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            err += m.sum() / total * abs(p[m].mean() - y[m].mean())
    return float(err)


def calibration_table(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    edges[-1] += 1e-12
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.any():
            rows.append({"predicted": float(p[m].mean()), "observed": float(y[m].mean()), "n": int(m.sum())})
    return rows


def metrics(y, p):
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": ece(y, p),
        "base_rate": float(y.mean()),
        "rows": int(len(y)),
        "positives": int(y.sum()),
    }


def top_decile_capture(y, p):
    cut = np.quantile(p, 0.9)
    return float(y[p >= cut].sum() / max(y.sum(), 1))


def fit_logistic(X, y, cols):
    scaler = StandardScaler().fit(X[:, cols])
    model = LogisticRegression(C=1.0, max_iter=1000).fit(scaler.transform(X[:, cols]), y)
    return scaler, model


def bootstrap_ci(y, p, students, rng, n=200):
    """95% interval for ROC-AUC, resampling whole students so correlated rows stay together."""
    order = np.argsort(students, kind="stable")
    ys, ps, ss = y[order], p[order], students[order]
    uniq, start = np.unique(ss, return_index=True)
    ends = np.append(start[1:], len(ss))
    vals = []
    for _ in range(n):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = np.concatenate([np.arange(start[i], ends[i]) for i in pick])
        if ys[idx].min() != ys[idx].max():
            vals.append(roc_auc_score(ys[idx], ps[idx]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def grouped_bootstrap(students, stat, rng, n=200):
    """Point estimate and 95% interval for stat(row_indices), resampling whole students so correlated
    rows from one student stay together."""
    order = np.argsort(students, kind="stable")
    uniq, start = np.unique(students[order], return_index=True)
    ends = np.append(start[1:], len(order))
    point = float(stat(np.arange(len(students))))
    vals = []
    for _ in range(n):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = order[np.concatenate([np.arange(start[i], ends[i]) for i in pick])]
        try:
            vals.append(float(stat(idx)))
        except ValueError:  # a resample with a single class has no AUC
            continue
    return {"value": point, "ci95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]}


def evaluate_split(X, y, masks, rng, label):
    """Fit on masks['train'], calibrate on masks['calib'], report on masks['test']."""
    log(f"[{label}] train/calib/test rows: {masks['train'].sum()}/{masks['calib'].sum()}/{masks['test'].sum()}")
    all_cols = MODEL_COLS
    week_cols = [FEATURES.index("weeks_since_start")]
    gap_cols = [FEATURES.index("days_since_last_activity"), FEATURES.index("weeks_since_start")]
    out = {}

    scaler, model = fit_logistic(X[masks["train"]], y[masks["train"]], all_cols)
    raw = lambda m: model.predict_proba(scaler.transform(X[m][:, all_cols]))[:, 1]  # noqa: E731
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(raw(masks["calib"]), y[masks["calib"]])
    test_raw = raw(masks["test"])
    test_cal = iso.predict(test_raw)
    yt = y[masks["test"]]

    out["padhotec_model_uncalibrated"] = metrics(yt, test_raw)
    out["padhotec_model_calibrated"] = metrics(yt, test_cal)
    out["padhotec_model_calibrated"]["top_decile_capture"] = top_decile_capture(yt, test_cal)
    out["calibration_table"] = calibration_table(yt, test_cal)

    for name, cols in (("baseline_week_only", week_cols), ("baseline_inactivity_gap", gap_cols)):
        s, m = fit_logistic(X[masks["train"]], y[masks["train"]], cols)
        pred = m.predict_proba(s.transform(X[masks["test"]][:, cols]))[:, 1]
        out[name] = metrics(yt, pred)
        if name == "baseline_inactivity_gap":
            gap_pred = pred

    gb = HistGradientBoostingClassifier(random_state=SEED).fit(X[masks["train"]][:, all_cols], y[masks["train"]])
    out["reference_gradient_boosting"] = metrics(yt, gb.predict_proba(X[masks["test"]][:, all_cols])[:, 1])
    return out, scaler, model, iso, test_cal, {"gap_pred": gap_pred}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    ent = load_entities()
    vle = load_daily_activity(ent)
    sa = load_scores(ent)
    X, y, student, presentation, week = build_dataset(ent, vle, sa)
    log(f"dataset: {len(y)} rows, {len(np.unique(student))} students, base rate {y.mean():.4f}")

    masks = split_students(student, rng)
    primary, scaler, model, iso, test_cal, extras = evaluate_split(X, y, masks, rng, "student-grouped split")
    yt, st = y[masks["test"]], student[masks["test"]]
    primary["padhotec_model_calibrated"]["roc_auc_95ci"] = bootstrap_ci(yt, test_cal, st, rng)

    # Extra rigor: skill against a naive baseline, gain over the simple baseline, and calibration slope.
    p0 = float(y[masks["train"]].mean())  # the naive predictor: everyone gets the training base rate
    gap_pred = extras["gap_pred"]
    log("bootstrapping skill scores")
    primary["extra"] = {
        "naive_baseline_probability": p0,
        "brier_skill_vs_naive": grouped_bootstrap(
            st, lambda i: 1 - np.mean((yt[i] - test_cal[i]) ** 2) / np.mean((yt[i] - p0) ** 2), rng),
        "auc_gain_vs_inactivity_gap": grouped_bootstrap(
            st, lambda i: roc_auc_score(yt[i], test_cal[i]) - roc_auc_score(yt[i], gap_pred[i]), rng),
    }
    clipped = np.clip(test_cal, 1e-4, 1 - 1e-4)
    recal = LogisticRegression(C=1e6, max_iter=1000).fit(np.log(clipped / (1 - clipped)).reshape(-1, 1), yt)
    primary["extra"]["calibration_slope"] = float(recal.coef_[0][0])  # 1.0 is perfect
    primary["extra"]["calibration_intercept"] = float(recal.intercept_[0])  # 0.0 is perfect

    # Out-of-time: learn from 2013 presentations, test on 2014 ones, with students seen in 2013 removed.
    is13 = np.char.startswith(presentation.astype(str), "2013")
    is14 = np.char.startswith(presentation.astype(str), "2014")
    seen = np.isin(student, np.unique(student[is13]))
    sub = split_students(student[is13], np.random.default_rng(SEED))
    m13 = {k: np.zeros(len(y), bool) for k in ("train", "calib", "test")}
    m13["train"][np.where(is13)[0][sub["train"]]] = True
    m13["calib"][np.where(is13)[0][sub["calib"]]] = True
    m13["test"] = is14 & ~seen
    oot, *_ = evaluate_split(X, y, m13, rng, "out-of-time 2013 -> 2014")

    # Explanation baseline: contribution of each feature, in log-odds, relative to the average student.
    coef = model.coef_[0]
    base_rate = float(y.mean())
    artifact = {
        "version": "risk-oulad-v1",
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "target": f"withdrawal from the module within {HORIZON_DAYS} days of the landmark",
        "features": MODEL_FEATURES,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": coef.tolist(),
        "intercept": float(model.intercept_[0]),
        "calibrator": {"x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist()},
        "base_rate": base_rate,
        # Levels are percentiles of held-out predictions, so "high" means "higher than 90% of OULAD rows".
        "levels": {
            "elevated": float(np.quantile(test_cal, 0.75)),
            "high": float(np.quantile(test_cal, 0.90)),
        },
        "training": {
            "dataset": "OULAD (CC BY 4.0), Kuzilek, Hlosta and Zdrahal, 2017",
            "rows": int(len(y)),
            "students": int(len(np.unique(student))),
            "seed": SEED,
        },
        "test_metrics": primary["padhotec_model_calibrated"],
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, indent=2))

    lv = artifact["levels"]
    bands = {
        "low": yt[test_cal < lv["elevated"]],
        "elevated": yt[(test_cal >= lv["elevated"]) & (test_cal < lv["high"])],
        "high": yt[test_cal >= lv["high"]],
    }
    primary["level_bands"] = {k: {"observed_rate": float(v.mean()), "n": int(len(v))} for k, v in bands.items()}

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "target": artifact["target"],
        "student_grouped_split": primary,
        "out_of_time_2013_to_2014": oot,
        "coefficients_standardised": dict(zip(MODEL_FEATURES, map(float, coef))),
    }, indent=2))
    log(f"wrote {ARTIFACT.name} and {REPORT.name} in {time.time() - t0:.0f}s")

    for label, res in (("PRIMARY (held-out students)", primary), ("OUT-OF-TIME (2013 -> 2014)", oot)):
        print(f"\n{label}")
        for name in ("padhotec_model_calibrated", "padhotec_model_uncalibrated", "baseline_inactivity_gap",
                     "baseline_week_only", "reference_gradient_boosting"):
            m = res[name]
            print(f"  {name:32s} AUC {m['roc_auc']:.3f}  PR-AUC {m['pr_auc']:.3f}  "
                  f"Brier {m['brier']:.4f}  ECE {m['ece']:.4f}  base rate {m['base_rate']:.3f}")
    print("\nlevel bands (observed 4-week withdrawal rate):", primary["level_bands"])
    print("\ncoefficients:", {k: round(float(v), 3) for k, v in zip(MODEL_FEATURES, coef)})
    print("extra:", json.dumps(primary["extra"], indent=1))
    print("AUC 95% CI:", primary["padhotec_model_calibrated"]["roc_auc_95ci"],
          " top-decile capture:", round(primary["padhotec_model_calibrated"]["top_decile_capture"], 3))


if __name__ == "__main__":
    main()
