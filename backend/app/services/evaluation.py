"""What the evidence page shows: offline results from public data, and a live check against real outcomes.

Offline numbers are read from the reports the training scripts wrote (backend/ml/reports). They are never
recomputed here and never include Padhotec or demo data. The live check compares stored predictions with what
students went on to do, using real accounts only, and says "not enough yet" until there is enough to say anything.
"""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assessment, DemoAccount, Prediction, StudySession
from app.services.insights import as_utc

REPORTS = Path(__file__).resolve().parents[2] / "ml" / "reports"
ARTIFACT = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "risk_v1.json"
RISK_HORIZON_DAYS = 28
MIN_RISK_RESOLVED = 30  # below this, a rate or a calibration claim is noise
MIN_PERFORMANCE_RESOLVED = 20

LIMITATIONS = [
    "The risk model learned from website clicks in a distance-learning university (OULAD) and is applied to minutes "
    "logged in Padhotec. The features are unit-free by design, but nobody has checked that the patterns carry over.",
    "The risk model is a modest predictor. It beats the simple baselines clearly, but rare events are hard to foresee: "
    "a High reading means about four times the withdrawal rate of a Low one, not a near-certain outcome.",
    "The expected-score estimate is slightly worse than a plain average of earlier scores. Its value is an honest "
    "range and sensible behaviour with little data, not a sharper single number.",
    "The score backtest predicts one assessment from earlier ones within a module. It is not a test on topic-level "
    "exam results, which Padhotec does not have yet.",
    "Withdrawal from a course is a stand-in for stopping studying. The app words it as stopping.",
    "Career role profiles are hand-built and not drawn from labour-market data. Readiness describes coverage of a "
    "profile, not a prediction of career success.",
    "Peer groups need at least 5 students and values are rounded, but that is not differential privacy.",
    "Demo accounts hold synthetic data. They are excluded from every figure on this page.",
]


def _read(name: str) -> dict | None:
    path = REPORTS / name
    return json.loads(path.read_text()) if path.exists() else None


def _risk(report: dict, artifact: dict) -> dict:
    primary = report["student_grouped_split"]
    model = primary["padhotec_model_calibrated"]
    extra = primary.get("extra", {})
    oot = report["out_of_time_2013_to_2014"]
    labels = {
        "baseline_week_only": "Week number only",
        "baseline_inactivity_gap": "Days since last activity",
        "padhotec_model_calibrated": "Padhotec risk model",
        "reference_gradient_boosting": "Gradient boosting (reference)",
    }
    return {
        "target": report["target"],
        "dataset": artifact["training"],
        "headline": {
            "roc_auc": {"value": model["roc_auc"], "ci95": model.get("roc_auc_95ci")},
            "pr_auc": model["pr_auc"],
            "base_rate": model["base_rate"],
            "brier": model["brier"],
            "brier_skill_vs_naive": extra.get("brier_skill_vs_naive"),
            "calibration_error": model["ece"],
            "calibration_slope": extra.get("calibration_slope"),
            "calibration_intercept": extra.get("calibration_intercept"),
            "top_decile_capture": model.get("top_decile_capture"),
            "rows_tested": model["rows"],
        },
        "models": [
            {"key": k, "label": label, "roc_auc": primary[k]["roc_auc"], "pr_auc": primary[k]["pr_auc"]}
            for k, label in labels.items()
        ],
        "auc_gain_vs_inactivity_gap": extra.get("auc_gain_vs_inactivity_gap"),
        "out_of_time": {
            "train": "2013 presentations",
            "test": "2014 presentations, students from 2013 removed",
            "roc_auc": oot["padhotec_model_calibrated"]["roc_auc"],
            "brier": oot["padhotec_model_calibrated"]["brier"],
            "rows": oot["padhotec_model_calibrated"]["rows"],
        },
        "calibration": primary["calibration_table"],
        "level_bands": primary.get("level_bands", {}),
        "levels": artifact["levels"],
    }


def _performance(report: dict) -> dict:
    app = report["test_half_app_defaults"]
    return {
        "n": app["n"],
        "defaults": report["app_defaults"],
        "mae": [
            {"key": "global_mean", "label": "Always the dataset average", "value": app["mae_baseline_global_mean"]},
            {"key": "last_score", "label": "Last score", "value": app["mae_baseline_last_score"]},
            {"key": "model", "label": "Padhotec estimate", "value": app["mae_model"]},
            {"key": "mean_of_earlier", "label": "Plain average of earlier scores",
             "value": app["mae_baseline_mean_of_earlier"]},
        ],
        "mae_diffs": {
            "vs_global_mean": app.get("mae_diff_vs_global_mean"),
            "vs_last_score": app.get("mae_diff_vs_last_score"),
            "vs_mean_of_earlier": app.get("mae_diff_vs_mean_of_earlier"),
        },
        "coverage": {"nominal": 0.8, "value": app["interval_80_coverage"], "ci95": (app.get("interval_80_coverage_ci") or {}).get("ci95"),
                     "mean_width": app["interval_80_mean_width"]},
        "half_life_curve": [
            {"days": int(k), "mae": v} for k, v in sorted(report["half_life_mae_on_tuning_half"].items(), key=lambda kv: int(kv[0]))
            if int(k) <= 1000
        ],
        "noise_curve": [
            {"sd": float(k), "coverage": v} for k, v in sorted(report["noise_sd_coverage_on_tuning_half"].items(), key=lambda kv: float(kv[0]))
        ],
        "coverage_by_earlier_scores": [
            {"k": int(k), "coverage": v["interval_80_coverage"], "n": v["n"]}
            for k, v in sorted(report["test_half_by_number_of_earlier_scores"].items(), key=lambda kv: int(kv[0]))
        ],
    }


def _live_risk(db: Session, real_user_ids: set[int], today: date) -> dict:
    cutoff = today - timedelta(days=RISK_HORIZON_DAYS)
    snaps = [p for p in db.scalars(select(Prediction).where(Prediction.kind == "risk")) if p.user_id in real_user_ids]
    sessions: dict[int, list[date]] = {}
    for s in db.scalars(select(StudySession)):
        if s.user_id in real_user_ids:
            sessions.setdefault(s.user_id, []).append(as_utc(s.started_at).date())
    resolved = []
    for p in snaps:
        if p.made_on > cutoff:
            continue  # the 28 days after this prediction have not all happened yet
        window_end = p.made_on + timedelta(days=RISK_HORIZON_DAYS)
        stopped = not any(p.made_on < d <= window_end for d in sessions.get(p.user_id, []))
        resolved.append((float(p.value["probability"]), stopped))
    out = {"snapshots": len(snaps), "resolved": len(resolved), "needed": MIN_RISK_RESOLVED, "stopped_rate": None,
           "mean_predicted": None}
    if len(resolved) >= MIN_RISK_RESOLVED:
        out["stopped_rate"] = sum(s for _, s in resolved) / len(resolved)
        out["mean_predicted"] = sum(p for p, _ in resolved) / len(resolved)
    return out


def _live_performance(db: Session, real_user_ids: set[int]) -> dict:
    snaps = [p for p in db.scalars(select(Prediction).where(Prediction.kind == "performance"))
             if p.user_id in real_user_ids and p.course_id is not None]
    exams = [a for a in db.scalars(select(Assessment).where(Assessment.kind == "exam")) if a.user_id in real_user_ids]
    resolved = []
    for p in snaps:
        later = sorted(
            (a for a in exams if a.user_id == p.user_id and a.course_id == p.course_id and as_utc(a.taken_at).date() > p.made_on),
            key=lambda a: as_utc(a.taken_at),
        )
        if later and later[0].max_score > 0:
            resolved.append((p.value, later[0].score / later[0].max_score))
    out = {"snapshots": len(snaps), "resolved": len(resolved), "needed": MIN_PERFORMANCE_RESOLVED, "coverage": None,
           "mean_abs_error": None}
    if len(resolved) >= MIN_PERFORMANCE_RESOLVED:
        out["coverage"] = sum(v["lo"] <= actual <= v["hi"] for v, actual in resolved) / len(resolved)
        out["mean_abs_error"] = sum(abs(v["mean"] - actual) for v, actual in resolved) / len(resolved)
    return out


def live_evaluation(db: Session, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    from app.models import User  # local import keeps this module's import graph simple

    demo_ids = {d.user_id for d in db.scalars(select(DemoAccount))}
    real_ids = {u for u in db.scalars(select(User.id)) if u not in demo_ids}
    return {
        "real_students": len(real_ids),
        "risk": _live_risk(db, real_ids, now.date()),
        "performance": _live_performance(db, real_ids),
        "note": "Demo accounts are excluded. A risk prediction counts as resolved after 28 days, with 'stopped' meaning no "
                "study session was logged in that window. An expected score counts as resolved once an exam score is logged.",
    }


def build_evaluation(db: Session) -> dict:
    risk_report, perf_report = _read("risk_oulad.json"), _read("performance_oulad.json")
    artifact = json.loads(ARTIFACT.read_text()) if ARTIFACT.exists() else None
    return {
        "available": bool(risk_report and perf_report and artifact),
        "risk": _risk(risk_report, artifact) if risk_report and artifact else None,
        "performance": _performance(perf_report) if perf_report else None,
        "live": live_evaluation(db),
        "limitations": LIMITATIONS,
        "source": "OULAD (CC BY 4.0), Kuzilek, Hlosta and Zdrahal, 2017. Offline figures use held-out students only.",
    }
