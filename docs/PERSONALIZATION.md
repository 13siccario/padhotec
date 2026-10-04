# Personalization (Phase 4)

Three features built on the Phase 3 models: a daily study plan, career readiness, and peer insights.
Code is in `backend/app/services/` (`planner.py`, `careers.py`, `peers.py`, glue in `personal.py`).

## Daily plan

Each topic has a value `urgency x exam share x (1 - mastery)`. Urgency is `1 / days to exam`, limited to
3 to 90 days (a course with no exam date counts as 60). Minutes are handed out in 5-minute steps to
whichever topic gains most from the next step, and each topic's return falls off exponentially (about an
hour of study cuts it by 63%), so time spreads over weak topics. No block is longer than 45 minutes, none
shorter than 10, and today's already-studied time comes off the budget.

Topics with no results yet get a 10-minute self-test first (at most two, at most half the budget). That is
the loop: log the score, mastery updates, tomorrow's plan changes. If every topic is untested, the
self-tests are the whole plan.

The daily budget is the student's weekly hours divided by 7 (45 minutes if unset), or whatever they pick.

- **Heuristic, not fitted.** The return curve and the urgency formula are planning rules. Nothing here has
  been validated against learning outcomes, and the app says so.
- **Acceptance data.** The first plan offered each day is stored as offered, so Phase 5 can measure how
  often students follow it.

## Careers

Eight hand-built role profiles over 19 skills (`app/data/careers.json`). **The required levels are my
judgement, not labour-market data**, and the page says so.

A skill's level (0 to 100) is a Beta estimate. A self-rating sets the mean (1 to 5 maps to 10, 30, 50, 70,
90) with a fixed certainty, and results from topics the student tagged with that skill add evidence.
A skill with neither is unknown.

Readiness is the importance-weighted share of a role's requirements the student currently meets. Unknown
skills are never counted as zero or as met: the worst case counts them as 0, the best case as fully met,
and the page shows that range. Rating more skills narrows it. The roadmap lists the gaps in learning order,
pulling in weak prerequisites first (probability before statistics before machine learning).

This is "how much of the profile do you cover", not a prediction of career success.

## Peers

Comparison groups, most specific first: same course and institution, same course, same degree, same
institution, everyone. The first one with **at least 5 other students** is used. If none qualifies, a
labelled public benchmark (days active per week among OULAD students) is shown instead, and the page
says it is not a peer group.

- Only aggregates leave the server: rounded quartiles (minutes to 15, days to 0.5), a position as a
  third, and topic names that at least 5 students track. No names, ids, or one student's exact figures.
- Students are only counted if they have at least 14 days of history and 3 study days.
- Students can opt out in their profile. Opting out removes you from everyone's figures and hides peer
  statistics from you.
- **Limit:** with a small user base, a group of exactly 5 is still a small group. Rounding and the
  threshold reduce what can be inferred, but they are not differential privacy. That comes with the
  federated phase.

## Tests

`tests/test_planner.py` includes a property test over 400 random inputs for the plan's invariants (time is
never invented or lost, block sizes, the cap). It caught two real bugs while this was being built.
