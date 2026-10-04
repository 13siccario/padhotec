"""Unit-free engagement features for the dropout-risk model.

Used by BOTH the OULAD training script and the live app, so the two cannot drift apart. The model is
trained on OULAD (VLE clicks) but applied to Padhotec (minutes studied), so no feature depends on the
unit of activity: only on which days had activity, and on ratios of the student's own recent activity to
their own history. Demographics are deliberately excluded.

Time is measured in whole days since the student's first activity (day 0). A landmark `t` means "as of the
start of day t": only days 0..t-1 are used, so nothing from the future leaks in.
"""

import numpy as np

FEATURES = [
    "days_since_last_activity",  # capped at 28
    "active_days_14",  # days with any activity in the last 14 days
    "active_rate_change",  # recent share of active days minus the student's own earlier share
    "activity_ratio_log",  # log of recent volume over the student's own earlier 14-day average
    "weeks_since_start",
    "n_scores",  # capped at 10
    "mean_score",  # 0-1; SCORE_IMPUTE when there are no scores yet
    "score_trend",  # latest score minus the mean of earlier ones; 0 with fewer than two scores
    "has_score",
]

# The model uses every feature except these two. Whether a student has logged any scores is a poor signal
# in Padhotec (logging is optional) even though it was informative in OULAD (submissions were required),
# so "no scores" must be neutral. They are still computed, to word the explanations.
EXPLANATION_ONLY = ("n_scores", "has_score")
MODEL_FEATURES = [f for f in FEATURES if f not in EXPLANATION_ONLY]
# Average OULAD score fraction, used in place of mean_score when a student has no scores yet.
SCORE_IMPUTE = 0.76

MIN_HISTORY_DAYS = 21  # earliest landmark; before this there is too little history to compare against
WINDOW = 14
HORIZON_DAYS = 28  # the model predicts withdrawal within this many days after the landmark
MAX_GAP = 28
MAX_SCORES = 10


def build_features(daily: np.ndarray, scores: list[tuple[int, float]], landmarks: np.ndarray) -> np.ndarray:
    """Feature matrix, one row per landmark.

    daily: activity per day from day 0 (any non-negative unit). Days past its end count as zero.
    scores: (day index, fraction 0-1) for each scored assessment.
    landmarks: day indices t, each >= MIN_HISTORY_DAYS.
    """
    landmarks = np.asarray(landmarks, dtype=int)
    if landmarks.size and landmarks.min() < MIN_HISTORY_DAYS:
        raise ValueError(f"landmarks must be >= {MIN_HISTORY_DAYS}")
    need = int(landmarks.max()) if landmarks.size else 0
    daily = np.asarray(daily, dtype=float)
    if len(daily) < need:
        daily = np.concatenate([daily, np.zeros(need - len(daily))])

    active = daily > 0
    cum_act = np.concatenate([[0.0], np.cumsum(daily)])
    cum_days = np.concatenate([[0.0], np.cumsum(active)])
    idx = np.arange(len(daily))
    last_active = np.maximum.accumulate(np.where(active, idx, -1))

    t = landmarks
    recent_act = cum_act[t] - cum_act[t - WINDOW]
    recent_days = cum_days[t] - cum_days[t - WINDOW]
    hist_len = t - WINDOW  # >= 7 because of MIN_HISTORY_DAYS
    hist_rate = cum_days[t - WINDOW] / hist_len
    hist_14 = cum_act[t - WINDOW] / hist_len * WINDOW

    last = last_active[t - 1]
    since = np.where(last >= 0, t - 1 - last, MAX_GAP)

    feats = np.zeros((len(t), len(FEATURES)))
    feats[:, 0] = np.minimum(since, MAX_GAP)
    feats[:, 1] = recent_days
    feats[:, 2] = recent_days / WINDOW - hist_rate
    feats[:, 3] = np.log((recent_act + 1.0) / (hist_14 + 1.0))
    feats[:, 4] = t / 7.0

    feats[:, 6] = SCORE_IMPUTE
    if scores:
        ordered = sorted(scores)
        days = np.array([d for d, _ in ordered])
        fracs = np.array([f for _, f in ordered], dtype=float)
        csum = np.concatenate([[0.0], np.cumsum(fracs)])
        n = np.searchsorted(days, t, side="left")  # scores strictly before the landmark
        has = n > 0
        safe_n = np.maximum(n, 1)
        mean = csum[n] / safe_n
        latest = fracs[np.maximum(n - 1, 0)]
        prev_mean = csum[np.maximum(n - 1, 0)] / np.maximum(n - 1, 1)
        feats[:, 5] = np.minimum(n, MAX_SCORES)
        feats[:, 6] = np.where(has, mean, SCORE_IMPUTE)
        feats[:, 7] = np.where(n >= 2, latest - prev_mean, 0.0)
        feats[:, 8] = has.astype(float)
    return feats
