"""Backtest the mastery/performance evidence model on OULAD score sequences.

Run from backend/:  uv run python ml/backtest_performance.py

For every student-module with at least 3 scored assessments, predict each assessment from the ones before
it, using the same Beta-evidence model the app uses (strength by assessment type, fading by days elapsed).
Checks: error against simple baselines, and whether the stated 80% interval really contains ~80% of outcomes.
Students are split in half: settings are tuned on one half and reported on the other.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ml.mastery import ASSESSMENT_STRENGTH, HALF_LIFE_DAYS  # noqa: E402
from app.ml.performance import EXAM_NOISE_SD  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "oulad"
REPORT = HERE / "reports" / "performance_oulad.json"
KEY = ["code_module", "code_presentation", "id_student"]
TYPE_TO_KIND = {"CMA": "quiz", "TMA": "assignment", "Exam": "exam"}
SEED = 0
N_DRAWS = 1000


def load_sequences() -> pd.DataFrame:
    sa = pd.read_csv(DATA / "studentAssessment.csv", na_values=["?"]).dropna(subset=["score"])
    assess = pd.read_csv(DATA / "assessments.csv", na_values=["?"])
    df = sa.merge(assess, on="id_assessment")
    df["fraction"] = df["score"].clip(0, 100) / 100.0
    df["strength"] = df["assessment_type"].map(TYPE_TO_KIND).map(ASSESSMENT_STRENGTH)
    df = df.sort_values(KEY + ["date_submitted", "id_assessment"]).reset_index(drop=True)
    df["k"] = df.groupby(KEY).cumcount()  # how many earlier scores this student has in this module
    return df


def predictions(df: pd.DataFrame, half_life: float):
    """Posterior (a, b) for every row from the rows before it in the same student-module."""
    a = np.ones(len(df))
    b = np.ones(len(df))
    groups = df.groupby(KEY).indices
    frac, strength, day = df["fraction"].to_numpy(), df["strength"].to_numpy(), df["date_submitted"].to_numpy(float)
    for idx in groups.values():
        for pos in range(1, len(idx)):
            i = idx[pos]
            earlier = idx[:pos]
            w = strength[earlier] * 0.5 ** (np.maximum(day[i] - day[earlier], 0) / half_life)
            a[i] += (w * frac[earlier]).sum()
            b[i] += (w * (1 - frac[earlier])).sum()
    return a, b


def interval(a, b, noise_sd, rng, mass=0.8):
    lo, hi = np.empty(len(a)), np.empty(len(a))
    tail = (1 - mass) / 2
    for s in range(0, len(a), 4000):
        sl = slice(s, s + 4000)
        draws = rng.beta(a[sl, None], b[sl, None], (len(a[sl]), N_DRAWS))
        draws = np.clip(draws + rng.normal(0, noise_sd, draws.shape), 0, 1)
        lo[sl], hi[sl] = np.quantile(draws, [tail, 1 - tail], axis=1)
    return lo, hi


def grouped_bootstrap(students, stat, rng, n=300):
    """Point estimate and 95% interval, resampling whole students so one student's rows stay together."""
    order = np.argsort(students, kind="stable")
    uniq, start = np.unique(students[order], return_index=True)
    ends = np.append(start[1:], len(order))
    point = float(stat(np.arange(len(students))))
    vals = []
    for _ in range(n):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = order[np.concatenate([np.arange(start[i], ends[i]) for i in pick])]
        vals.append(float(stat(idx)))
    return {"value": point, "ci95": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]}


def main():
    rng = np.random.default_rng(SEED)
    df = load_sequences()
    df = df[df.groupby(KEY)["k"].transform("max") >= 2].reset_index(drop=True)  # at least 3 scores
    students = rng.permutation(df["id_student"].unique())
    tune_ids = set(students[: len(students) // 2])
    is_tune = df["id_student"].isin(tune_ids).to_numpy()
    print(f"{len(df)} assessments from {df.groupby(KEY).ngroups} student-modules; "
          f"{int((df.k >= 1).sum())} are predictable from earlier scores")

    # Tune the half-life on the tuning half by mean absolute error of the posterior mean.
    results = {}
    for hl in sorted({7, 15, 30, 60, 90, 120, 100000, HALF_LIFE_DAYS}):
        a, b = predictions(df, hl)
        mask = is_tune & (df.k >= 1).to_numpy()
        results[hl] = float(np.abs(a / (a + b) - df["fraction"].to_numpy())[mask].mean())
        print(f"  half-life {hl:>6} days: tuning-half MAE {results[hl]:.4f}")
    best_hl = min(results, key=results.get)

    a, b = predictions(df, HALF_LIFE_DAYS)  # the app's defaults
    a_best, b_best = predictions(df, best_hl)
    y = df["fraction"].to_numpy()
    eligible = (df.k >= 1).to_numpy()
    test = ~is_tune & eligible
    tune = is_tune & eligible

    # Tune the noise term so the 80% interval is calibrated on the tuning half, then verify on the test half.
    coverage_by_noise = {}
    for sd in sorted({0.0, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.15, 0.20, EXAM_NOISE_SD}):
        lo, hi = interval(a[tune], b[tune], sd, rng)
        coverage_by_noise[sd] = float(((y[tune] >= lo) & (y[tune] <= hi)).mean())
        print(f"  noise sd {sd:.2f}: tuning-half 80% interval coverage {coverage_by_noise[sd]:.3f}")
    best_sd = min(coverage_by_noise, key=lambda s: abs(coverage_by_noise[s] - 0.8))

    def evaluate(aa, bb, sd, mask, ci=True):
        mean = aa[mask] / (aa[mask] + bb[mask])
        lo, hi = interval(aa[mask], bb[mask], sd, rng)
        yy = y[mask]
        prev_mean = (df.groupby(KEY)["fraction"].transform(lambda s: s.shift().expanding().mean())).to_numpy()[mask]
        last = (df.groupby(KEY)["fraction"].shift()).to_numpy()[mask]
        err_model, err_prev = np.abs(mean - yy), np.abs(prev_mean - yy)
        err_global, err_last = np.abs(0.758 - yy), np.abs(last - yy)
        covered = ((yy >= lo) & (yy <= hi)).astype(float)
        out = {
            "n": int(mask.sum()),
            "mae_model": float(err_model.mean()),
            "mae_baseline_global_mean": float(err_global.mean()),
            "mae_baseline_last_score": float(err_last.mean()),
            "mae_baseline_mean_of_earlier": float(err_prev.mean()),
            "interval_80_coverage": float(covered.mean()),
            "interval_80_mean_width": float((hi - lo).mean()),
        }
        if ci:
            sid = df["id_student"].to_numpy()[mask]
            # Differences are model minus baseline, so negative means the model is better.
            out["interval_80_coverage_ci"] = grouped_bootstrap(sid, lambda i: covered[i].mean(), rng)
            out["mae_diff_vs_global_mean"] = grouped_bootstrap(sid, lambda i: err_model[i].mean() - err_global[i].mean(), rng)
            out["mae_diff_vs_last_score"] = grouped_bootstrap(sid, lambda i: err_model[i].mean() - err_last[i].mean(), rng)
            out["mae_diff_vs_mean_of_earlier"] = grouped_bootstrap(sid, lambda i: err_model[i].mean() - err_prev[i].mean(), rng)
        return out

    report = {
        "half_life_mae_on_tuning_half": {str(k): v for k, v in results.items()},
        "best_half_life_days": best_hl,
        "noise_sd_coverage_on_tuning_half": {str(k): v for k, v in coverage_by_noise.items()},
        "chosen_noise_sd": best_sd,
        "app_defaults": {"half_life_days": HALF_LIFE_DAYS, "noise_sd": EXAM_NOISE_SD},
        "test_half_app_defaults": evaluate(a, b, EXAM_NOISE_SD, test),
        "test_half_best_half_life_and_calibrated_noise": evaluate(a_best, b_best, best_sd, test),
        "test_half_by_number_of_earlier_scores": {
            str(k): evaluate(a, b, EXAM_NOISE_SD, test & (df.k.to_numpy() == k), ci=False) for k in (1, 2, 3, 5)
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    print("\nTEST HALF (students never used for tuning)")
    for name in ("test_half_app_defaults", "test_half_best_half_life_and_calibrated_noise"):
        print(name)
        for k, v in report[name].items():
            print(f"   {k:34s} {v:.4f}" if isinstance(v, float) else f"   {k:34s} {v}")
    app = report["test_half_app_defaults"]
    print("\nwith 95% intervals (students resampled):")
    print("  coverage of the 80% range:", app["interval_80_coverage_ci"])
    for k in ("mae_diff_vs_global_mean", "mae_diff_vs_last_score", "mae_diff_vs_mean_of_earlier"):
        print(f"  {k}:", app[k])
    print("coverage by number of earlier scores:",
          {k: round(v["interval_80_coverage"], 3) for k, v in report["test_half_by_number_of_earlier_scores"].items()})


if __name__ == "__main__":
    main()
