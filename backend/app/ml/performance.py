"""Expected exam score as a distribution, propagated from the topic mastery posteriors.

Exam fraction = weighted mean of topic mastery, with each topic's mastery drawn from its Beta posterior.
Topics with no evidence keep a wide prior, so missing data widens the interval instead of being ignored.

Assumptions, stated plainly: mastery on a topic equals the expected fraction of that topic's marks, and topic
weights are the student's own estimate of exam weighting. The noise term was calibrated on OULAD score
sequences, but nothing here is validated against real Padhotec exam results yet.
"""

from dataclasses import dataclass

import numpy as np

# Variation beyond mastery (which questions come up, nerves, slips). With the 90-day half-life, an 80% interval on
# OULAD score sequences needs about this much noise to cover ~80% of outcomes (0.05 covered only 70%).
# Tied to HALF_LIFE_DAYS: re-run ml/backtest_performance.py after changing either.
EXAM_NOISE_SD = 0.10
N_SAMPLES = 4000
MIN_EVIDENCE = 3.0  # below this many effective questions across the course, refuse to predict


@dataclass(frozen=True)
class TopicPosterior:
    weight: float
    a: float
    b: float
    evidence: float


@dataclass(frozen=True)
class Performance:
    mean: float
    lo: float  # 80% interval
    hi: float
    p_pass: float  # probability the score is at least pass_mark
    pass_mark: float
    covered_weight: float  # share of exam weight (0-1) that has any real evidence behind it


def predict(topics: list[TopicPosterior], pass_mark: float = 0.5, seed: int = 0) -> Performance | None:
    if not topics or sum(t.evidence for t in topics) < MIN_EVIDENCE:
        return None
    rng = np.random.default_rng(seed)
    weights = np.array([t.weight for t in topics], dtype=float)
    weights /= weights.sum()
    draws = np.column_stack([rng.beta(t.a, t.b, N_SAMPLES) for t in topics])
    score = draws @ weights + rng.normal(0, EXAM_NOISE_SD, N_SAMPLES)
    score = np.clip(score, 0.0, 1.0)
    lo, hi = np.quantile(score, [0.1, 0.9])
    covered = float(sum(w for w, t in zip(weights, topics) if t.evidence >= 1.0))
    return Performance(
        mean=float(score.mean()),
        lo=float(lo),
        hi=float(hi),
        p_pass=float((score >= pass_mark).mean()),
        pass_mark=pass_mark,
        covered_weight=covered,
    )
