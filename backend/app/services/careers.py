"""Career readiness from skill levels. Pure functions: no database access.

Skill level (0-100) is a Beta posterior that combines a self-rating with the evidence from topics the
student has tagged with that skill. A skill with neither is *unknown*, and unknown is never silently
treated as zero or as met: it widens the readiness range (worst case 0, best case fully met).

"Readiness" is how much of a role's illustrative skill profile the student currently covers. It is not
a prediction of career success, and the role profiles are hand-built, not taken from labour-market data.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from scipy.stats import beta as beta_dist

from app.ml.mastery import rating_to_fraction

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "careers.json"
SELF_RATING_STRENGTH = 6.0  # how certain a self-rating is, in effective questions. The rating sets the mean.
MIN_TOPIC_EVIDENCE = 1.0
FOUNDATION_LEVEL = 50  # target for a prerequisite the role itself doesn't list
MAX_ROADMAP_STEPS = 6
GAP_TOLERANCE = 0.02  # within 2% of the requirement counts as met


@dataclass(frozen=True)
class SkillLevel:
    mean: float  # 0-100
    lo: float
    hi: float


@dataclass(frozen=True)
class Gap:
    skill: str
    label: str
    required: float
    current: float | None  # None: not rated yet
    importance: int


@dataclass(frozen=True)
class RoadmapStep:
    skill: str
    label: str
    current: float | None
    target: float
    reason: str


@dataclass(frozen=True)
class Readiness:
    career: str
    label: str
    summary: str
    mean: float  # 0-1
    lo: float
    hi: float
    unrated: int
    total: int
    gaps: list[Gap]
    roadmap: list[RoadmapStep]


@lru_cache(maxsize=1)
def load_catalog(path: Path = CATALOG_PATH) -> dict:
    return json.loads(path.read_text())


def skills_by_key() -> dict[str, dict]:
    return {s["key"]: s for s in load_catalog()["skills"]}


def validate_catalog(catalog: dict) -> list[str]:
    """Problems with the catalogue, or an empty list. Used by a test so edits can't ship broken."""
    problems, keys = [], [s["key"] for s in catalog["skills"]]
    if len(set(keys)) != len(keys):
        problems.append("duplicate skill keys")
    known = set(keys)
    for s in catalog["skills"]:
        problems += [f"{s['key']}: unknown prerequisite {p}" for p in s["prereqs"] if p not in known]
    for c in catalog["careers"]:
        seen = set()
        for r in c["requirements"]:
            if r["skill"] not in known:
                problems.append(f"{c['key']}: unknown skill {r['skill']}")
            if r["skill"] in seen:
                problems.append(f"{c['key']}: duplicate requirement {r['skill']}")
            seen.add(r["skill"])
            if not 0 < r["level"] <= 100 or r["importance"] not in (1, 2, 3):
                problems.append(f"{c['key']}: bad level/importance for {r['skill']}")
    # Prerequisite cycles
    state: dict[str, int] = {}

    def visit(k: str, trail: tuple[str, ...]) -> None:
        if state.get(k) == 2:
            return
        if state.get(k) == 1:
            problems.append("prerequisite cycle: " + " -> ".join(trail + (k,)))
            return
        state[k] = 1
        for p in next((s["prereqs"] for s in catalog["skills"] if s["key"] == k), []):
            if p in known:
                visit(p, trail + (k,))
        state[k] = 2

    for k in keys:
        visit(k, ())
    return problems


def estimate_skill(
    self_rating: int | None, topic_evidence: list[tuple[float, float]], mass: float = 0.9
) -> SkillLevel | None:
    """topic_evidence: (a, b) Beta parameters of each topic tagged with this skill (prior included)."""
    evidence = sum(max(a - 1, 0) + max(b - 1, 0) for a, b in topic_evidence)
    if self_rating is None and evidence < MIN_TOPIC_EVIDENCE:
        return None
    # With a rating, the Beta is centred on it (so a 5 can actually meet a requirement of 80). Without one, start
    # from the uniform prior and let the topic results speak.
    if self_rating is not None:
        f = rating_to_fraction(self_rating)
        a, b = SELF_RATING_STRENGTH * f, SELF_RATING_STRENGTH * (1 - f)
    else:
        a = b = 1.0
    for ta, tb in topic_evidence:
        a += max(ta - 1, 0)
        b += max(tb - 1, 0)
    tail = (1 - mass) / 2
    return SkillLevel(
        mean=100 * a / (a + b),
        lo=100 * float(beta_dist.ppf(tail, a, b)),
        hi=100 * float(beta_dist.ppf(1 - tail, a, b)),
    )


def _attained(level: float, required: float) -> float:
    return min(level / required, 1.0)


def _roadmap(career: dict, levels: dict[str, SkillLevel | None], gaps: list[Gap]) -> list[RoadmapStep]:
    skills = skills_by_key()
    required = {r["skill"]: r for r in career["requirements"]}

    def weak(skill: str) -> bool:
        lvl = levels.get(skill)
        return lvl is None or lvl.mean < FOUNDATION_LEVEL

    # Start from the gaps, then pull in any weak prerequisite so it can be learned first.
    wanted: dict[str, str] = {g.skill: f"Needed for {career['label'].lower()}" for g in gaps}
    stack = list(wanted)
    while stack:
        for pre in skills[stack.pop()]["prereqs"]:
            if pre not in wanted and weak(pre):
                wanted[pre] = "A foundation for the skills after it"
                stack.append(pre)

    # Prerequisites first; among the ready ones, the more important to this role comes first.
    remaining, order = set(wanted), []
    while remaining:
        ready = [s for s in remaining if not any(p in remaining for p in skills[s]["prereqs"])]
        ready.sort(key=lambda s: (-(required[s]["importance"] if s in required else 0), s))
        order.append(ready[0])
        remaining.remove(ready[0])

    steps = []
    for s in order[:MAX_ROADMAP_STEPS]:
        lvl = levels.get(s)
        steps.append(
            RoadmapStep(
                skill=s,
                label=skills[s]["label"],
                current=None if lvl is None else lvl.mean,
                target=float(required[s]["level"]) if s in required else float(FOUNDATION_LEVEL),
                reason=wanted[s],
            )
        )
    return steps


def readiness(career: dict, levels: dict[str, SkillLevel | None]) -> Readiness:
    skills = skills_by_key()
    num = {"mean": 0.0, "lo": 0.0, "hi": 0.0}
    total_weight, unrated, gaps = 0.0, 0, []
    for r in career["requirements"]:
        w, req, lvl = r["importance"], float(r["level"]), levels.get(r["skill"])
        total_weight += w
        if lvl is None:
            unrated += 1
            num["mean"] += w * 0.5  # no information: the uniform prior's midpoint
            num["hi"] += w * 1.0
            gaps.append(Gap(r["skill"], skills[r["skill"]]["label"], req, None, w))
            continue
        num["mean"] += w * _attained(lvl.mean, req)
        num["lo"] += w * _attained(lvl.lo, req)
        num["hi"] += w * _attained(lvl.hi, req)
        if _attained(lvl.mean, req) < 1 - GAP_TOLERANCE:
            gaps.append(Gap(r["skill"], skills[r["skill"]]["label"], req, lvl.mean, w))

    def urgency(g: Gap) -> float:
        shortfall = 0.5 if g.current is None else 1 - _attained(g.current, g.required)
        return g.importance * shortfall

    gaps.sort(key=urgency, reverse=True)
    return Readiness(
        career=career["key"],
        label=career["label"],
        summary=career["summary"],
        mean=num["mean"] / total_weight,
        lo=num["lo"] / total_weight,
        hi=num["hi"] / total_weight,
        unrated=unrated,
        total=len(career["requirements"]),
        gaps=gaps,
        roadmap=_roadmap(career, levels, gaps),
    )


def rank_careers(levels: dict[str, SkillLevel | None]) -> list[Readiness]:
    results = [readiness(c, levels) for c in load_catalog()["careers"]]
    return sorted(results, key=lambda r: r.mean, reverse=True)
