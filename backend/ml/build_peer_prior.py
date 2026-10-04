"""Summarise how many days a week OULAD students were active, for the peer-insight fallback.

Run from backend/:  uv run python ml/build_peer_prior.py

Used only when too few Padhotec students are comparable. It is a public-dataset benchmark of one
behaviour (active days per week), and the app labels it as such.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import train_risk as T  # noqa: E402
from app.ml.risk_features import FEATURES  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "app" / "ml" / "artifacts" / "peer_prior_oulad.json"


def main():
    ent = T.load_entities()
    vle = T.load_daily_activity(ent)
    sa = T.load_scores(ent)
    X, _, student, _, _ = T.build_dataset(ent, vle, sa)
    weekly = X[:, FEATURES.index("active_days_14")] / 2.0  # active days per week over a 14-day window
    q = np.quantile(weekly, [0.25, 0.5, 0.75])
    OUT.write_text(json.dumps({
        "metric": "active_days_per_week",
        "p25": round(float(q[0]), 2), "p50": round(float(q[1]), 2), "p75": round(float(q[2]), 2),
        "rows": int(len(weekly)), "students": int(len(np.unique(student))),
        "source": "OULAD (CC BY 4.0), Kuzilek, Hlosta and Zdrahal, 2017",
    }, indent=2))
    print(OUT.read_text())


if __name__ == "__main__":
    main()
