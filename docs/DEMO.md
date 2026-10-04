# Demo script

A 6 to 7 minute walkthrough for the competition, plus the questions to expect. Every number below is on the
[evidence page](http://localhost:3000/evaluation); say them as they appear there.

## Set up (once, 2 minutes)

Use a separate database so demo accounts never mix with your own data:

```sh
cd backend
export PADHOTEC_DATABASE_URL=sqlite:///./demo.db
uv run python scripts/seed_demo.py --yes      # 26 synthetic students; prints the sign-in details
uv run uvicorn app.main:app                   # terminal 1
cd ../frontend && npm run dev                 # terminal 2, then open http://localhost:3000
```

Sign in as `steady@demo.padhotec.example.com`, password `demo-password`. The other two accounts are
`quiet@...` and `new@...`. A yellow banner on every demo account says the data is invented. To start over,
run the seed command again with `--reset`; it removes demo accounts only.

## The pitch (30 seconds)

> Most study apps show you a score. Padhotec shows you what you probably know, what to do with the next
> hour, and how sure it is. Every estimate comes with its uncertainty, and we tested each one on public data,
> with the failures left in.

## The walkthrough

**1. The steady student (2 minutes).** Sign in as `steady`.
- Greeting and exam countdown. "It already knows the exam is in 14 days."
- **Today:** the plan. Point at one block's reason: estimated mastery, share of the exam, days left. "Topics with
  no results get a short self-test first. Log the score and tomorrow's plan changes."
- **Your courses:** the range bars. "The dot is our best estimate, the band is where we think it really is. A
  topic with one quiz has a wide band. More evidence narrows it."
- **Expected score:** a range, plus the chance of reaching a pass mark, and how much of the exam has no data.

**2. The student who went quiet (1 minute).** Sign out, sign in as `quiet`.
- **Staying on track** shows Elevated or High, and *why*: "0 of the last 14 days studied", plus a small
  disclaimer. "It names the behaviour, not a verdict. It is shown to the student only."

**3. The new student (30 seconds).** Sign in as `new`.
- "Six days of history, so it says it needs about 21 days. It refuses to guess."

**4. Peers and privacy (1 minute).** As `steady`, open Peers.
- "A group needs at least 5 other students, numbers are rounded, nobody is named, and you can opt out."
- "A real student would never see these demo peers. We keep synthetic and real data apart."

**5. Career (30 seconds).** Open Career.
- Ranges, not scores: unrated skills widen them. "These role profiles are hand-built. We say so on the page."

**6. The evidence (2 minutes).** Open Evidence. This is the part to slow down on.
- Risk model: AUC **0.720** (95% interval 0.707 to 0.734), on students it never saw. Beats the
  days-since-last-activity baseline by **+0.062** (0.052 to 0.073). Also 0.713 when trained on 2013 and tested
  on 2014.
- Reliability chart: "When it says about 5%, about 5% stop." Calibration slope 0.93.
- Levels: Low **1.6%**, Elevated **4.5%**, High **6.8%** stopped within 28 days, against an average of 2.6%.
- Score model: the stated 80% range holds **79.5%** of real outcomes (79.1 to 79.9).
- **Volunteer the weaknesses before they are asked:** "Our score estimate is slightly worse than a plain average
  of earlier scores, by 0.002, which is 0.2 points out of 100. It does beat the naive guesses. What it adds is an
  honest range. And the risk model's Brier skill is only 1.6%: stopping is rare and hard to foresee."

## Questions to expect

**"An AUC of 0.72 is not impressive."** Agreed, and the page says "modest predictor". The gain over the simple
baseline is real (+0.062, interval excludes zero) and the probabilities are calibrated. The honest claim is that
it is a useful, honest nudge, not a forecast.

**"Why is the score model worse than an average?"** The difference is 0.002, real but tiny, found by backtesting
73,366 assessments. We kept it because it gives a calibrated range and behaves sensibly with little data, which a
plain average does not. We report both.

**"It learned from OULAD clicks. Does that transfer to your logs?"** Not verified. The features are unit-free by
design (days active, ratios against the student's own history), and the page lists this first under what it does
not show. Stored predictions are compared with real outcomes as students arrive; until 30 have resolved, the page
shows no rate.

**"Is the demo data real?"** No. It is simulated, marked, kept out of every figure, and its learning dynamics
differ from the model's assumptions, so it cannot flatter the model. It only fills the screens.

**"Why not federated learning?"** It is the planned next step. It only matters when several institutions cannot
share data, and we have one deployment. Building it first would have been the wrong order.

**"What about privacy?"** Pseudonymous event log, consent at sign-up, delete-everything button, peer groups of at
least 5 with rounded values, and an opt-out. Rounding and thresholds are not differential privacy, and the page
says that too.

**"How do I know the numbers are not tuned on the test data?"** Settings were chosen on one random half of the
students and every figure comes from the other half. Intervals come from resampling whole students. The scripts
and seeds are in the repository: `ml/train_risk.py` and `ml/backtest_performance.py`.

## If something goes wrong

- Blank dashboard: the backend is not running, or you are on the wrong database. Check `PADHOTEC_DATABASE_URL`.
- No demo peers: only demo accounts see demo peers. Sign in as a demo account, not a new one.
- Evidence page empty: the reports are in `backend/ml/reports/`. Re-run the two scripts above.
