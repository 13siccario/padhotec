# What Padhotec does

Padhotec is a study companion for students. You tell it what you are studying, log your study time and your
scores, and it tells you three things: **what you probably know, what to do with your next hour, and how sure
it is.** Every estimate comes with its uncertainty, and nothing is hidden behind a single "score".

It works for any subject. The maths (probability and statistics) is in how it reasons, not in what you study.

## Who it is for

- **Students** who want to know where to spend limited study time before an exam.
- **Classmates and friends** using it together, with privacy-protected comparisons.
- **Judges and reviewers** who want to see how the numbers were tested. The public Evidence page shows that.

## What you put in, what you get out

You log only two kinds of things. There is no question bank.

| You log | Padhotec uses it for |
|---|---|
| Courses, their topics, exam dates and each topic's share of the exam | Knowing what matters and when |
| Study sessions (topic, minutes, date) | Daily plan, "staying on track" signal |
| Scores (quiz, assignment, mock, exam) | Mastery estimates, expected score |
| Optional self-ratings (1 to 5) per topic | A starting point when you have no scores yet |
| Optional career interests and skill ratings | Skill-gap view |

| You get | What it means |
|---|---|
| **Mastery per topic** | A best estimate plus a range. A topic with one quiz has a wide range; more evidence narrows it. Old evidence fades (half-life 90 days). |
| **Expected score per course** | A range (80%), the chance of reaching a pass mark, and how much of the exam has no data yet. |
| **A daily plan** | Study blocks ordered by how urgent, how heavy in the exam, and how weak each topic is. Each block says why. Topics with no results get a short self-test first. |
| **Staying on track** | A gentle signal if your study pattern looks like one that tends to stop. It names the behaviour ("0 of the last 14 days studied") and is shown only to you. |
| **Career skill gaps** | For 8 role profiles, how ready you look, as a range, and a roadmap of what to learn next. |
| **Peer insights** | How your study time compares with others, only when a group is large enough to protect people. |

## The pages

| Page | Purpose |
|---|---|
| **Dashboard** | Greeting, exam countdown, today's plan, expected score, staying-on-track signal. Start here each day. |
| **Courses** | Add courses and topics; see mastery as a dot with a range band for every topic. |
| **Log** | Record a study session, a score, or a self-rating. Takes seconds. |
| **Career** | Pick a role; see readiness range, missing skills and a roadmap. |
| **Peers** | Anonymous comparison with your group. Opt out any time. |
| **Profile** | Your details, consent, the "About the numbers" notes, sign out, delete everything. |
| **Evidence** (public, no sign-in) | How accurate the models are, tested on public data, with the weaknesses stated. |

## User journey

### 1. First visit: decide whether to trust it
A visitor can open **Evidence** without an account. It shows how the models did on data they never saw and
lists what the app cannot tell you. The login page links to it.

### 2. Sign up (about a minute)
Create an account with an email and password, and tick consent to how your data is used. Your activity is
stored under a pseudonym, not your name.

### 3. Set up a course (about 3 minutes)
Add a course, its topics, the exam date, and roughly how much of the exam each topic is worth. The dashboard
now knows what you are working toward. At this point it shows wide ranges and says so; with no results it
says it has no evidence rather than guessing.

### 4. Give it first evidence
Either rate your confidence per topic (1 to 5), or log a past score. Self-ratings give a rough start, but a
real score counts for much more. The first plan appears, with short self-tests for topics that have no results.

### 5. The daily loop (the core habit)
1. Open **Dashboard**, read **Today**, see why each block is there.
2. Study. Log the session on **Log** (topic and minutes).
3. Log any quiz, assignment, mock or exam score when you get it.
4. Tomorrow's plan changes: mastery ranges tighten, the plan shifts to what is now weakest and most urgent.

### 6. Before the exam
The expected-score range and pass chance become informative as evidence builds. The plan leans toward
high-weight, low-mastery topics as the date nears. After the exam, log the real score; this is how the app
(and its public accuracy check) learns whether it was right.

### 7. If you slip
After about 21 days of history and at least 3 study days, **Staying on track** can show Elevated or High if
your recent study dropped off. It shows the reason, not a verdict, and nothing happens automatically. Before
that point it says it needs more history instead of guessing.

### 8. Beyond one course
- **Career:** rate a few skills; topics you master add evidence automatically. Unrated skills widen the
  range instead of counting as zero.
- **Peers:** once at least 5 other students share your course (or degree, or institution), you see rounded,
  anonymous comparisons. Until then, you see a labelled reference from public data, or nothing.

### 9. Leaving
**Profile** lets you opt out of peer comparison and delete your account and all your data.

## Edge cases the app handles

| Situation | What happens |
|---|---|
| New topic, no data | Wide range (about 3% to 97%), says "no evidence" |
| Fewer than 21 days of history | Says it needs more history; no risk reading |
| Very few scores | Range widens; the page shows how much of the exam has no results |
| Small peer group | Falls back to a larger group, or a labelled public reference, or nothing |
| Demo accounts | Marked with a yellow banner; kept out of statistics and from real students' peers |

## Privacy in one list

- Consent at sign-up; pseudonymous activity log; no demographics used in predictions.
- Peer groups need at least 5 others; values are rounded; nobody is named; opt-out available.
- Delete-everything button.
- Rounding and thresholds are not differential privacy, and the app says so.

## What it is not

- Not a question bank or a tutor: it never tests you on content.
- Not a verdict on you: the dropout signal is a modest predictor, shown only to you.
- Not proven on Padhotec's own users yet: the risk model was trained on public university data (OULAD) and
  the transfer to Padhotec logs is unverified. The Evidence page's live check fills in as real outcomes arrive.

See also: [MODELS.md](MODELS.md) for the maths, [PERSONALIZATION.md](PERSONALIZATION.md) for plan, careers
and peers, [DEMO.md](DEMO.md) for the presentation script, [FEDERATED.md](FEDERATED.md) for v2.
