"""Topic mastery as a Beta posterior over "probability of getting a typical question on this topic right".

Every piece of evidence is a (fraction correct, strength) pair, where strength is an effective number
of questions. Evidence fades with a half-life, so old results count for less and the interval widens
again if a student stops practising. Posterior = Beta(a0 + sum w*s*f, b0 + sum w*s*(1-f)).

The half-life was checked against OULAD score sequences. The per-type strengths are still assumptions:
no Padhotec outcome data exists yet to fit them. Re-tune both once exams have happened.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from scipy.stats import beta as beta_dist

# Effective number of questions a single result is worth. A mock exam says more than a quiz.
ASSESSMENT_STRENGTH = {"quiz": 4.0, "assignment": 6.0, "mock": 10.0, "exam": 12.0}
# A self-rating is weak, biased evidence, so it is worth little and only the latest few count.
SELF_RATING_STRENGTH = 1.5
MAX_SELF_RATINGS = 5
# A course-wide score says something about every topic in the course, but less than a topic score.
COURSE_LEVEL_SHARE = 0.5
# Chosen from the OULAD backtest (ml/backtest_performance.py): prediction error is flat beyond about 60 days
# and clearly worse at 30, so old results stay informative. 90 keeps some fading without throwing evidence away.
HALF_LIFE_DAYS = 90.0
PRIOR_A, PRIOR_B = 1.0, 1.0  # uniform: no opinion until there is evidence
CREDIBLE_MASS = 0.9


@dataclass(frozen=True)
class Evidence:
    fraction: float  # 0..1
    strength: float  # effective number of questions
    at: datetime


@dataclass(frozen=True)
class Mastery:
    mean: float
    lo: float  # lower end of the credible interval
    hi: float
    a: float
    b: float
    #: Evidence still counted after fading, in effective questions. Near zero means "no real data".
    evidence: float
    n_observations: int
    last_evidence_at: datetime | None


def rating_to_fraction(rating: int) -> float:
    """Map a 1-5 self-rating to a fraction, staying away from the extremes (nobody is 0% or 100% sure)."""
    return 0.1 + 0.8 * (rating - 1) / 4


def fade(age_days: float, half_life: float = HALF_LIFE_DAYS) -> float:
    return 0.5 ** (max(age_days, 0.0) / half_life)


def estimate(
    evidence: Iterable[Evidence],
    now: datetime,
    half_life: float = HALF_LIFE_DAYS,
    mass: float = CREDIBLE_MASS,
) -> Mastery:
    items = list(evidence)
    a, b, counted = PRIOR_A, PRIOR_B, 0.0
    for e in items:
        weight = e.strength * fade((now - e.at).total_seconds() / 86400, half_life)
        a += weight * e.fraction
        b += weight * (1 - e.fraction)
        counted += weight
    tail = (1 - mass) / 2
    return Mastery(
        mean=a / (a + b),
        lo=float(beta_dist.ppf(tail, a, b)),
        hi=float(beta_dist.ppf(1 - tail, a, b)),
        a=a,
        b=b,
        evidence=counted,
        n_observations=len(items),
        last_evidence_at=max((e.at for e in items), default=None),
    )
