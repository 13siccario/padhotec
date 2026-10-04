"""Runtime dropout-risk scoring from the trained artifact. NumPy only: no scikit-learn needed to serve.

The model estimates the chance that a student stops (withdraws) within 28 days, learned from OULAD
engagement patterns. It has NOT been validated on Padhotec students; treat it as an early-warning nudge.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.ml.risk_features import FEATURES, HORIZON_DAYS, MIN_HISTORY_DAYS, build_features

ARTIFACT_PATH = Path(__file__).parent / "artifacts" / "risk_v1.json"
MIN_ACTIVE_DAYS = 3

# Features shown to the student as one driver, so offsetting features don't read as contradictions.
GROUPS = {
    "gap": ["days_since_last_activity"],
    "rhythm": ["active_days_14", "active_rate_change"],
    "volume": ["activity_ratio_log"],
    "stage": ["weeks_since_start"],
    "scores": ["mean_score", "score_trend"],
}
GROUP_LABEL = {
    "gap": "Time since last session",
    "rhythm": "Study rhythm",
    "volume": "Study time",
    "stage": "How far in you are",
    "scores": "Scores",
}


@dataclass(frozen=True)
class Driver:
    label: str
    effect: str  # "raises" or "lowers"
    detail: str
    weight: float  # size of the effect on the log-odds, for ordering


@dataclass(frozen=True)
class RiskResult:
    status: str  # "ok" or "insufficient_data"
    message: str | None = None
    probability: float | None = None  # calibrated chance of stopping within the horizon
    typical: float | None = None  # average rate in the training data
    level: str | None = None  # "low" | "elevated" | "high"
    drivers: list[Driver] = field(default_factory=list)
    horizon_days: int = HORIZON_DAYS
    model_version: str | None = None
    features: dict[str, float] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_artifact(path: Path = ARTIFACT_PATH) -> dict:
    return json.loads(path.read_text())


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _describe(group: str, f: dict[str, float], effect: str) -> str:
    if group == "gap":
        d = int(f["days_since_last_activity"])
        return "You studied today" if d == 0 else f"Your last session was {_plural(d, 'day')} ago"
    if group == "rhythm":
        n = int(f["active_days_14"])
        change = f["active_rate_change"]
        note = ", fewer than usual for you" if change < -0.1 else ", more than usual for you" if change > 0.1 else ""
        return f"You studied on {n} of the last 14 days{note}"
    if group == "volume":
        ratio = float(np.exp(f["activity_ratio_log"]))
        if ratio < 0.8:
            return f"Study time is {round((1 - ratio) * 100)}% lower than your earlier average"
        if ratio > 1.25:
            return f"Study time is {round((ratio - 1) * 100)}% higher than your earlier average"
        return "Study time is about the same as your earlier average"
    if group == "stage":
        w = int(f["weeks_since_start"])
        tail = "stopping is more common in the earlier weeks" if effect == "raises" else "past the earlier weeks, when stopping is more common"
        return f"Week {w} of studying; {tail}"
    n = int(f["n_scores"])
    if n == 0:
        return "No scores logged yet"
    text = f"{_plural(n, 'score')} logged, averaging {f['mean_score']:.0%}"
    trend = f["score_trend"]
    if abs(trend) >= 0.1:
        text += f"; latest is {round(abs(trend) * 100)} points {'below' if trend < 0 else 'above'} your earlier average"
    return text


def assess(daily: np.ndarray, scores: list[tuple[int, float]]) -> RiskResult:
    """daily: activity per day from the student's first session (day 0) up to and including today."""
    art = load_artifact()
    n_days = len(daily)
    active_days = int(np.count_nonzero(np.asarray(daily) > 0))
    if n_days < MIN_HISTORY_DAYS or active_days < MIN_ACTIVE_DAYS:
        return RiskResult(
            status="insufficient_data",
            message=f"A risk estimate needs about {MIN_HISTORY_DAYS} days of history and at least "
            f"{MIN_ACTIVE_DAYS} study days. Keep logging and it will appear.",
            model_version=art["version"],
        )

    x_all = build_features(np.asarray(daily, dtype=float), scores, np.array([n_days]))[0]
    x = np.array([x_all[FEATURES.index(name)] for name in art["features"]])
    z = (x - np.array(art["mean"])) / np.array(art["scale"])
    contrib = z * np.array(art["coef"])  # per-feature effect on log-odds versus the average OULAD row
    logit = art["intercept"] + contrib.sum()
    raw = 1.0 / (1.0 + np.exp(-logit))
    probability = float(np.interp(raw, art["calibrator"]["x"], art["calibrator"]["y"]))

    levels = art["levels"]
    level = "high" if probability >= levels["high"] else "elevated" if probability >= levels["elevated"] else "low"

    feats = dict(zip(FEATURES, map(float, x_all)))
    by_name = dict(zip(art["features"], contrib))
    drivers = []
    for group, names in GROUPS.items():
        if group == "scores" and feats["n_scores"] == 0:
            continue  # no scores logged is neutral by design, so there is nothing to explain
        weight = float(sum(by_name[n] for n in names))
        if abs(weight) < 0.05:
            continue  # too small to be worth showing
        effect = "raises" if weight > 0 else "lowers"
        drivers.append(Driver(GROUP_LABEL[group], effect, _describe(group, feats, effect), abs(weight)))
    drivers.sort(key=lambda d: d.weight, reverse=True)

    return RiskResult(
        status="ok",
        probability=probability,
        typical=art["base_rate"],
        level=level,
        drivers=drivers,
        model_version=art["version"],
        features=feats,
    )
