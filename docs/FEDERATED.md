# Federated learning plan (v2)

Status: plan only, nothing built. Written so the decision to start can be made on evidence, not enthusiasm.

## Why, and why not yet

Padhotec has one deployment. Federated learning only earns its complexity when several institutions
hold data they will not or cannot pool. So v2 has two gates, and neither is met today:

1. **At least 3 institutions** willing to run their own Padhotec instance (or a classmate group at each).
2. **Enough resolved outcomes per site.** The live check on `/evaluation` needs 30 resolved risk predictions
   before it shows a rate. A site with fewer than about 100 labelled landmarks has nothing to contribute.

Also required first: Alembic migrations (instances must upgrade independently), and a first look at whether
the OULAD-trained risk model transfers to Padhotec logs at all. If it does not transfer, federating it
spreads a weak model, not a strong one.

## What gets federated, and what does not

| Model | Federate? | Why |
|---|---|---|
| Mastery (Beta posterior) | No | Per student, closed form, no parameters shared across students. |
| Risk (logistic regression + isotonic) | **Yes, the logistic weights** | Seven features, ~8 numbers. Small, convex, well understood. |
| Risk calibration (isotonic) | Yes, as shared histogram bins | Isotonic is not averageable. Each site sends per-bin counts of (predicted, stopped); the server fits it. |
| Evidence strengths, half-life, noise sd | Yes, as sufficient statistics | Currently guessed. Sites send sums of squared errors per candidate setting; the server picks the best. No raw scores leave. |
| Peer insights | No | Already aggregate; stays inside one instance. |

The first two rows are the main experiment. The third is where federation fixes a real gap: the "not checked"
items in `docs/MODELS.md` can only be fitted from many students' real exam outcomes.

## Architecture

Cross-silo, not cross-device. Each institution runs its own backend and database. A coordinator service does
rounds:

1. Coordinator publishes the current global weights and a round id.
2. Each site trains locally on its own labelled landmarks for a few epochs, using the same
   `risk_features.py` code (feature definitions are versioned, a mismatch rejects the update).
3. Site clips the update to a fixed L2 norm, adds Gaussian noise, and sends it with its sample count.
4. Coordinator combines updates by sample-weighted average (FedAvg), with secure aggregation so it never sees
   one site's update alone.
5. Repeat for a fixed number of rounds; publish as `risk_v2.json` in the existing NumPy-only format.

Why not cross-device (each student's browser)? Rounds need many always-on participants; a classmate group of
30 cannot supply that, and a site-level model is the natural unit anyway.

## Privacy, stated honestly

- Only model updates leave a site, never rows, events or pseudonyms.
- Clipping plus noise gives a differential-privacy guarantee **per site update**, with a stated epsilon
  budget. We report the epsilon actually spent, not "private".
- Secure aggregation hides individual sites from the coordinator, not from a coordinator colluding with all
  other sites.
- Updates can leak. With 3 to 5 sites and ~8 weights, strong noise costs real accuracy. The evaluation below
  measures that cost instead of assuming it is free.

## Evaluation (the quant part)

OULAD already gives natural, non-identical silos: 7 modules and 22 presentations with different withdrawal
rates and activity patterns. Simulate sites as modules (or module groups), split students within each site,
and compare on held-out students:

| Arm | Meaning |
|---|---|
| Local only | Each site trains alone |
| Federated, no noise | FedAvg |
| Federated + DP | FedAvg with clipping and noise at several epsilon values |
| Centralised | Pooled data, the upper bound (today's model) |

Report, with student-level bootstrap intervals as on the current evidence page: AUC, Brier skill, calibration
slope, and the **gain over local-only for the smallest site**. That last number is the whole argument for
federation. Also run a leave-one-site-out test: train on all but one module, test on the unseen one, which is
the realistic "new institution joins" case. Plot AUC against epsilon so the privacy cost is visible.

Decision rule, fixed in advance: federation ships only if the federated model beats local-only for the
smallest site with an interval excluding zero, at an epsilon we are willing to state publicly. If not, we say
so on the evidence page and keep local models.

## Phases

| Phase | Work | Output |
|---|---|---|
| F0 | Alembic; model/feature versioning; export of site training stats | Instances upgrade independently |
| F1 | OULAD silo simulation, FedAvg for the logistic model, no privacy | Whether federation helps at all |
| F2 | Clipping, noise, epsilon accounting; shared calibration bins | Privacy cost curve |
| F3 | Coordinator service, site client, secure aggregation, signed updates | Runs across two real instances |
| F4 | Federated fitting of half-life and evidence strengths | Replaces guessed constants |
| F5 | Evidence page section: federated vs local, epsilon, per-site contribution | Public, with the failures left in |

F1 is the only phase worth doing before real sites exist; it answers the question on public data and costs
about a day. Everything from F3 on waits for actual institutions.

## Risks

- **Transfer failure.** Mitigation: finish the live OULAD-to-Padhotec check first.
- **Too few sites.** Three sites with noise may not beat local. The decision rule handles this.
- **Poisoned updates.** A bad site can skew the average. Mitigation: norm clipping, signed updates, and
  median-style aggregation as an option.
- **Feature drift between versions.** Mitigation: feature-set hash in every update, mismatches rejected.
- **Scope.** This is a research add-on, not a student-facing feature. It must not delay the product.
