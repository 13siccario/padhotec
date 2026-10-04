# Padhotec: v1 plan

Padhotec is a study platform that treats each student as a probabilistic state-estimation problem.
Every number it shows comes with calibrated uncertainty. It is built for a quant competition and
for real use by classmates. Federated learning comes after v1, once there are several users.

## Locked decisions
- Data comes from self-logged study sessions and exam or assignment scores. There is no question bank.
- Any subject is supported. "Quant" describes the methods, not the course content.
- Peer insights use a fallback ladder: own cohort (k>=5), then broader groups, then a labelled
  OULAD prior, then nothing.
- Risk is a flag for the student. No automated high-stakes decisions.

## Phases

| # | Phase | Output | Status |
|---|---|---|---|
| 1 | Foundation | FastAPI backend, auth with consent and rate limiting, data model, event log, delete-my-data | Done |
| 2 | Frontend and logging | Next.js app: sign up, courses and topics, log sessions and scores, dashboard | Done |
| 3 | Intelligence | Mastery (Beta posterior with forgetting decay), performance prediction, dropout risk (OULAD, calibrated) | Next |
| 4 | Personalization | Study planner, career skill-gap, peer insights | |
| 5 | Evaluation and demo | Calibration and backtest page, labelled synthetic seed data, demo script | |

## Methods
- Mastery: Beta posterior per topic, shrunk toward the prior between observations (half-life = forgetting).
- Performance: Bayesian hierarchical regression, giving a score distribution.
- Risk: discrete-time hazard model fit on OULAD, then recalibrated. Reported with Brier score and a reliability curve.
- Plan: allocate hours to maximize expected gain before the exam date.
- Career: skill vector vs role profile. A rules-based fit score, not a validated outcome model.

## After v1
Federated learning with Flower. Keep models in a package with `get_params`, `set_params` and a
local `fit`. Simulate clients by partitioning OULAD, then compare centralized, FedAvg, and
FedAvg with differential privacy.
