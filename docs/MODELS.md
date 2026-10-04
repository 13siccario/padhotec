# Padhotec models (Phase 3)

Three models, all explainable and all reporting uncertainty. Code is in `backend/app/ml/`, training and
evaluation scripts in `backend/ml/`, and the numbers below come from `backend/ml/reports/`.

## 1. Mastery (per topic)

A Beta posterior over "chance of getting a typical question on this topic right". Each result adds
evidence worth a number of effective questions: quiz 4, assignment 6, mock 10, exam 12. A course-wide
score counts half for each topic in that course. Self-ratings (1 to 5) count 1.5 each, and only the
latest five. Evidence fades with a 90-day half-life. With no evidence the answer is the uniform prior:
50%, interval 3% to 97%.

- **Checked:** the half-life, on OULAD score sequences. Error is flat beyond about 60 days and clearly
  worse at 30 (mean absolute error 0.135 vs 0.123).
- **Not checked:** the per-type strengths and the self-rating weight. They are reasonable guesses. They
  can only be fitted once Padhotec students have real exam outcomes.

## 2. Expected score (per course)

Draw each topic's mastery from its posterior, take the exam-weighted mean, add 0.10 of exam-day noise.
Report the mean, an 80% range, and the chance of reaching the pass mark. Topics with no evidence keep
a wide prior, so missing data widens the range, and the app says how much exam weight has no results.

Backtest on 73,366 OULAD assessments from students never used for tuning (`ml/backtest_performance.py`):

| | Mean absolute error |
|---|---|
| This model | 0.123 |
| Always predict the dataset average | 0.144 |
| Predict the last score | 0.139 |
| Average of earlier scores | 0.121 |

The 80% range contained 79.5% of real outcomes. **The honest reading:** the point estimate is no better
than a plain average of earlier scores. The value is the calibrated range and the sensible handling of
thin data. The test was on scores within a module, not on topic-level exam results.

## 3. Staying on track (dropout risk)

Logistic regression, calibrated with isotonic regression. It estimates the chance a student withdraws
within 28 days, from seven features that do not depend on the unit of activity: days since last
activity, days active in the last 14, change in active-day rate versus the student's own history, change
in volume versus their own history, weeks since start, average score, and score trend. No demographics.
Whether any scores are logged is deliberately ignored, because logging is optional in Padhotec but was
required in OULAD.

Trained on OULAD: 766,337 weekly landmarks from 24,895 students, 2.7% of which precede a withdrawal.
Students are split into train, calibration and test groups, so no student appears in two.

| Held-out students | AUC | PR-AUC | Brier | Calibration error |
|---|---|---|---|---|
| This model | 0.720 (95% CI 0.707 to 0.734) | 0.056 | 0.0249 | 0.002 |
| Days since last activity only | 0.658 | 0.046 | 0.0251 | 0.002 |
| Week number only | 0.586 | 0.034 | 0.0252 | 0.003 |
| Gradient boosting (reference) | 0.743 | 0.069 | 0.0248 | 0.002 |

Trained on 2013 presentations and tested on 2014 ones with no shared students: AUC 0.713.

Observed 28-day withdrawal rate by level: low 1.6%, elevated 4.5%, high 6.8%. The levels are the 75th
and 90th percentiles of held-out predictions.

**The honest reading:** the model separates students better than chance and its probabilities are
well calibrated, but it is a modest predictor. Withdrawals are rare and hard to foresee. A "high"
reading means about four times the withdrawal rate of a "low" one, not a near-certain outcome.

### Limits that matter

- **Transfer is untested.** It learned from OULAD's website clicks and is applied to minutes logged in
  Padhotec. Features were chosen to be unit-free, but nobody has checked that the patterns carry over.
- **"Withdrawal" is a stand-in for "stopped studying."** The app words it as stopping.
- **Needs history.** It refuses to answer before 21 days of history and at least 3 study days.
- **A nudge, not a verdict.** It is shown only to the student, with its limits stated, and nothing
  automated happens because of it.

## Stored predictions

Each computed prediction is saved once per day, with the model version and (for risk) the feature
values. Phase 5 uses them to compare predictions with what actually happened to Padhotec students.

## Reproduce

```sh
cd backend
# download OULAD (CC BY 4.0) into ml/data/oulad/ first; see README
uv run python ml/train_risk.py            # writes app/ml/artifacts/risk_v1.json and reports/risk_oulad.json
uv run python ml/backtest_performance.py  # writes reports/performance_oulad.json
```

Dataset: Kuzilek, Hlosta and Zdrahal (2017), *Open University Learning Analytics dataset*, Scientific
Data 4:170171, CC BY 4.0.
