"use client";

import Link from "next/link";
import { ChartCard, Columns, DotPlot, LineChart, Reliability, Stat } from "@/components/charts";
import { LogoMark, Wordmark } from "@/components/Logo";
import { Card, SectionTitle, btnQuiet } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, type Evaluation } from "@/lib/api";
import { useLoad } from "@/lib/hooks";

const f3 = (v: number) => v.toFixed(3);
const f4 = (v: number) => v.toFixed(4);
const pct1 = (v: number) => `${(v * 100).toFixed(1)}%`;
const signed4 = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(4)}`;
const range = (e: { ci95: [number, number] | null } | null, fmt: (v: number) => string) =>
  e?.ci95 ? `95% interval ${fmt(e.ci95[0])} to ${fmt(e.ci95[1])}` : "";

export default function EvaluationPage() {
  const { data, error, loading } = useLoad(api.evaluation);
  const { hydrated, signedIn } = useAuth();

  return (
    <div className="min-h-screen px-4 py-6 md:px-8">
      <div className="mx-auto max-w-6xl rounded-[40px] bg-canvas p-5 ring-1 ring-white/70 md:p-10">
        <nav className="flex items-center justify-between gap-4" aria-label="Page">
          <Link href={signedIn ? "/dashboard" : "/login"} className="flex items-center gap-2.5">
            <LogoMark size={34} />
            <Wordmark className="text-2xl" />
          </Link>
          {hydrated && (
            <Link href={signedIn ? "/dashboard" : "/login"} className={btnQuiet}>
              {signedIn ? "Back to the app" : "Sign in"}
            </Link>
          )}
        </nav>

        <header className="mt-10 max-w-3xl">
          <h1 className="text-4xl font-normal leading-[1.08] md:text-6xl">
            How accurate is it?
            <span className="block text-ink-mute">Every figure here comes from public data or real students.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-lg text-ink-soft">
            Padhotec makes three kinds of estimate: how well you know a topic, what you might score, and whether you are
            drifting. This page shows how each was tested, with the uncertainty left in. Demo accounts are never
            counted.
          </p>
        </header>

        {error && <p role="alert" className="mt-8 text-bad">{error}</p>}
        {loading && <p className="mt-8 text-ink-soft">Loading the results</p>}
        {data && !data.available && (
          <p className="mt-8 max-w-prose text-ink-soft">
            The model reports are not available on this server yet. Run the training scripts described at the bottom of
            this page.
          </p>
        )}
        {data?.available && data.risk && data.performance && <Content d={data} risk={data.risk} perf={data.performance} />}
      </div>
    </div>
  );
}

function Content({ d, risk, perf }: { d: Evaluation; risk: NonNullable<Evaluation["risk"]>; perf: NonNullable<Evaluation["performance"]> }) {
  const h = risk.headline;
  const diffs = perf.mae_diffs;
  const worse = diffs.vs_mean_of_earlier;
  const bands = risk.level_bands;
  const aucRows = risk.models.map((m) => ({
    label: m.label,
    value: m.roc_auc,
    ci: m.key === "padhotec_model_calibrated" ? h.roc_auc.ci95 : null,
    highlight: m.key === "padhotec_model_calibrated",
    note: m.key === "reference_gradient_boosting" ? "A more flexible model, shown for reference only" : undefined,
  }));
  const diffRows = [
    { label: "Always the dataset average", e: diffs.vs_global_mean },
    { label: "Last score", e: diffs.vs_last_score },
    { label: "Plain average of earlier scores", e: diffs.vs_mean_of_earlier },
  ].map((r) => ({ label: r.label, value: r.e?.value ?? 0, ci: r.e?.ci95 ?? null, highlight: true }));

  return (
    <div className="mt-10 space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="Ranking students by risk" value={f3(h.roc_auc.value)} sub={`ROC-AUC, ${range(h.roc_auc, f3)}. 0.5 is chance.`} tone="bg-sticky" />
        <Stat
          label="Calibration of the percentages"
          value={h.calibration_slope === null ? "n/a" : f3(h.calibration_slope)}
          sub="Calibration slope on held-out students. 1.000 is perfect."
          tone="bg-lilac"
        />
        <Stat
          label="Expected-score range holds"
          value={pct1(perf.coverage.value)}
          sub={`of real outcomes fall inside the stated 80% range. ${range(perf.coverage, pct1)}`}
          tone="bg-mint"
        />
      </div>

      {/* ---------------- Risk ---------------- */}
      <section aria-labelledby="risk-ev" className="space-y-4 pt-4">
        <SectionTitle id="risk-ev">Staying on track: the dropout risk model</SectionTitle>
        <p className="max-w-3xl text-ink-soft">
          Trained on {risk.dataset.rows.toLocaleString()} weekly snapshots of {risk.dataset.students.toLocaleString()} students
          from a public distance-learning dataset (OULAD). Students are split so nobody appears on both sides. It
          estimates {risk.target}. Everything below is on students the model never saw.
        </p>
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
          <ChartCard
            wide
            title="It ranks students better than the simple alternatives"
            subtitle="ROC-AUC on held-out students. 0.5 is a coin flip. The line through the dark dot is the 95% interval, from resampling whole students."
            table={{ head: ["Model", "ROC-AUC", "PR-AUC"], rows: risk.models.map((m) => [m.label, f3(m.roc_auc), f3(m.pr_auc)]) }}
          >
            <DotPlot rows={aucRows} domain={[0.5, 0.8]} ticks={[0.5, 0.6, 0.7, 0.8]} format={f3} tickFormat={(v) => v.toFixed(1)} reference={{ value: 0.5, label: "Chance (0.5)" }} ariaLabel="ROC-AUC by model" />
            {risk.auc_gain_vs_inactivity_gap && (
              <p className="mt-4 text-sm text-ink-soft">
                Gain over the days-since-last-activity baseline: <strong className="text-ink">+{f3(risk.auc_gain_vs_inactivity_gap.value)}</strong>,{" "}
                {range(risk.auc_gain_vs_inactivity_gap, f3)}.
              </p>
            )}
          </ChartCard>

          <ChartCard
            title="When it says 5%, about 5% do stop"
            subtitle="Held-out students sorted into ten equal groups by predicted risk. A dot on the line means the percentage is right."
            table={{ head: ["Predicted", "Observed", "Rows"], rows: risk.calibration.map((c) => [pct1(c.predicted), pct1(c.observed), c.n.toLocaleString()]) }}
          >
            <Reliability points={risk.calibration} max={0.08} ariaLabel="Predicted against observed rate of stopping" />
            <p className="mt-3 text-sm text-ink-soft">
              Calibration slope {h.calibration_slope?.toFixed(2)}, intercept {h.calibration_intercept?.toFixed(2)}. The
              negative intercept means it slightly over-predicted on this particular split, where students happened to
              stop a little less often than in training.
            </p>
          </ChartCard>

          <ChartCard
            title="What Low, Elevated and High mean"
            subtitle="The share of held-out students who actually stopped within 28 days, by the level the model gave them."
            table={{ head: ["Level", "Stopped within 28 days", "Rows"], rows: (["low", "elevated", "high"] as const).map((k) => [k, pct1(bands[k].observed_rate), bands[k].n.toLocaleString()]) }}
          >
            <Columns
              ariaLabel="Observed rate of stopping by risk level"
              format={pct1}
              reference={{ value: h.base_rate, label: `Average ${pct1(h.base_rate)}` }}
              items={(["low", "elevated", "high"] as const).map((k) => ({
                label: k[0].toUpperCase() + k.slice(1),
                value: bands[k].observed_rate,
                detail: `${bands[k].n.toLocaleString()} rows`,
              }))}
            />
            <p className="mt-3 text-sm text-ink-soft">
              High is about {(bands.high.observed_rate / bands.low.observed_rate).toFixed(1)} times as likely as Low, a clear
              but modest gap. It is a prompt to check in, not a verdict.
            </p>
          </ChartCard>

          <Card as="div" className="space-y-4 lg:col-span-2">
            <h3 className="font-sans text-xl font-medium tracking-normal">The honest numbers</h3>
            <dl className="grid max-w-3xl grid-cols-[1fr_auto] gap-x-6 gap-y-2.5 text-ink-soft">
              <dt>Brier skill against a naive predictor</dt>
              <dd className="font-medium tabular-nums text-ink">{h.brier_skill_vs_naive ? pct1(h.brier_skill_vs_naive.value) : "n/a"}</dd>
              <dt className="col-span-2 -mt-1.5 text-sm">{range(h.brier_skill_vs_naive, pct1)}. Reliably above zero, but small: stopping is rare and hard to foresee.</dt>
              <dt>PR-AUC, against a base rate of {pct1(h.base_rate)}</dt>
              <dd className="font-medium tabular-nums text-ink">{f3(h.pr_auc)}</dd>
              <dt>Share of stoppers in the top-scored 10%</dt>
              <dd className="font-medium tabular-nums text-ink">{h.top_decile_capture === null ? "n/a" : pct1(h.top_decile_capture)}</dd>
              <dt>Calibration error</dt>
              <dd className="font-medium tabular-nums text-ink">{pct1(h.calibration_error)}</dd>
              <dt>Trained on 2013, tested on 2014 (new students)</dt>
              <dd className="font-medium tabular-nums text-ink">AUC {f3(risk.out_of_time.roc_auc)}</dd>
            </dl>
          </Card>
        </div>
      </section>

      {/* ---------------- Score ---------------- */}
      <section aria-labelledby="score-ev" className="space-y-4 pt-4">
        <SectionTitle id="score-ev">Expected score and mastery</SectionTitle>
        <p className="max-w-3xl text-ink-soft">
          Tested by predicting each assessment from the earlier ones in the same module, on {perf.n.toLocaleString()}{" "}
          assessments from students not used to choose any setting. It is a test of the evidence model, not of topic-level
          exam marks, which Padhotec does not have yet.
        </p>
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
          <ChartCard
            wide
            title="It beats the naive guesses, and trails a plain average by a hair"
            subtitle="Change in average error against each baseline, in points of score out of 1. Left of zero means Padhotec was closer to the real score."
            table={{
              head: ["Baseline", "Difference in error", "95% interval"],
              rows: diffRows.map((r) => [r.label, signed4(r.value), r.ci ? `${signed4(r.ci[0])} to ${signed4(r.ci[1])}` : ""]),
            }}
          >
            <DotPlot
              rows={diffRows}
              domain={[-0.025, 0.005]}
              ticks={[-0.02, -0.01, 0]}
              format={signed4}
              tickFormat={(v) => (v === 0 ? "0" : `−${Math.abs(v).toFixed(2)}`)}
              reference={{ value: 0, label: "No difference" }}
              ariaLabel="Difference in prediction error against each baseline"
            />
            {worse && (
              <p className="mt-4 text-sm text-ink-soft">
                Against the plain average, Padhotec is worse by <strong className="text-ink">{signed4(worse.value)}</strong>, which is
                0.2 points of a 100-point score. The difference is real but tiny. What the model adds is an honest range
                and sensible behaviour when there is little data.
              </p>
            )}
          </ChartCard>

          <ChartCard
            title="The stated 80% range holds about 80%"
            subtitle="Share of real outcomes inside the range, by how many earlier scores the student had."
            table={{
              head: ["Earlier scores", "Inside the 80% range", "Assessments"],
              rows: perf.coverage_by_earlier_scores.map((c) => [c.k, pct1(c.coverage), c.n.toLocaleString()]),
            }}
          >
            <DotPlot
              rows={perf.coverage_by_earlier_scores.map((c) => ({ label: `${c.k} earlier score${c.k === 1 ? "" : "s"}`, value: c.coverage, highlight: true, note: `${c.n.toLocaleString()} assessments` }))}
              domain={[0.6, 1]}
              ticks={[0.6, 0.7, 0.8, 0.9, 1]}
              format={pct1}
              tickFormat={(v) => `${Math.round(v * 100)}%`}
              reference={{ value: 0.8, label: "Target (80%)" }}
              ariaLabel="Coverage of the 80% range by number of earlier scores"
            />
            <p className="mt-3 text-sm text-ink-soft">
              Overall {pct1(perf.coverage.value)}, {range(perf.coverage, pct1)}. Just under the target, by under a point.
            </p>
          </ChartCard>

          <ChartCard
            title={`Why results fade slowly: a ${perf.defaults.half_life_days.toFixed(0)}-day half-life`}
            subtitle="Average error on the tuning half, for different half-lives. Fading old scores quickly made predictions worse; beyond about 60 days it is flat."
            table={{ head: ["Half-life (days)", "Average error"], rows: perf.half_life_curve.map((p) => [p.days, f4(p.mae)]) }}
          >
            <LineChart
              ariaLabel="Average error by half-life"
              points={perf.half_life_curve.map((p) => ({ x: p.days, y: p.mae }))}
              xDomain={[0, 130]}
              yDomain={[0.12, 0.22]}
              xTicks={[0, 30, 60, 90, 120]}
              yTicks={[0.12, 0.14, 0.16, 0.18, 0.2, 0.22]}
              xFormat={(v) => `${v}`}
              yFormat={(v) => v.toFixed(2)}
              xLabel="Half-life (days)"
              yLabel="Average error"
              chosen={perf.defaults.half_life_days}
            />
          </ChartCard>

          <ChartCard
            title={`Why the range has ${perf.defaults.noise_sd.toFixed(2)} of exam-day noise`}
            subtitle="Share of outcomes inside the stated 80% range, for different amounts of extra noise, on the tuning half. Too little noise makes the range overconfident."
            table={{ head: ["Noise", "Inside the 80% range"], rows: perf.noise_curve.map((p) => [p.sd.toFixed(2), pct1(p.coverage)]) }}
          >
            <LineChart
              ariaLabel="Coverage by amount of noise"
              points={perf.noise_curve.map((p) => ({ x: p.sd, y: p.coverage }))}
              xDomain={[0, 0.21]}
              yDomain={[0.6, 1]}
              xTicks={[0, 0.05, 0.1, 0.15, 0.2]}
              yTicks={[0.6, 0.7, 0.8, 0.9, 1]}
              xFormat={(v) => v.toFixed(2)}
              yFormat={(v) => `${Math.round(v * 100)}%`}
              xLabel="Exam-day noise"
              yLabel="Inside the range"
              chosen={perf.defaults.noise_sd}
              reference={{ y: 0.8, label: "Target (80%)" }}
            />
          </ChartCard>

          <Card as="div" className="space-y-3">
            <h3 className="font-sans text-xl font-medium tracking-normal">A fair test</h3>
            <p className="text-ink-soft">
              The half-life and the amount of noise were chosen on one random half of the students. Every figure judged
              above comes from the other half, whose scores had no say in any setting.
            </p>
            <p className="text-ink-soft">
              Where a result carries a 95% interval, it comes from resampling whole students, so one student&apos;s many
              assessments are never treated as independent evidence.
            </p>
            <p className="text-ink-soft">
              The settings are listed with the chart that justifies them. If you change one, the backtest script
              reproduces every number on this page.
            </p>
          </Card>
        </div>
      </section>

      {/* ---------------- Live ---------------- */}
      <section aria-labelledby="live-ev" className="pt-4">
        <Card aria-labelledby="live-ev">
          <SectionTitle id="live-ev">Checked against real Padhotec students</SectionTitle>
          <p className="mt-3 max-w-prose text-ink-soft">
            Each prediction Padhotec makes is stored. When the outcome is known, it is compared with what happened. Until
            enough have resolved, the app says so and shows no rate.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <Live
              title="Stopping within 28 days"
              resolved={d.live.risk.resolved}
              needed={d.live.risk.needed}
              snapshots={d.live.risk.snapshots}
              result={d.live.risk.stopped_rate === null ? null : `${pct1(d.live.risk.stopped_rate)} stopped, against ${pct1(d.live.risk.mean_predicted ?? 0)} predicted on average`}
            />
            <Live
              title="Expected score against the real exam"
              resolved={d.live.performance.resolved}
              needed={d.live.performance.needed}
              snapshots={d.live.performance.snapshots}
              result={d.live.performance.coverage === null ? null : `${pct1(d.live.performance.coverage)} inside the 80% range`}
            />
          </div>
          <p className="mt-4 max-w-prose text-sm text-ink-soft">{d.live.note}</p>
        </Card>
      </section>

      {/* ---------------- Limits and reproduction ---------------- */}
      <section aria-labelledby="limits-ev" className="pt-4">
        <Card aria-labelledby="limits-ev">
          <SectionTitle id="limits-ev">What this does not show</SectionTitle>
          <ul className="mt-4 space-y-3">
            {d.limitations.map((t) => (
              <li key={t} className="rounded-2xl bg-panel px-4 py-3 text-ink-soft">
                {t}
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section aria-labelledby="repro-ev" className="pb-2 pt-4">
        <Card aria-labelledby="repro-ev">
          <SectionTitle id="repro-ev">Check it yourself</SectionTitle>
          <p className="mt-3 max-w-prose text-ink-soft">
            The scripts, fixed seeds and reports are in the repository. {d.source}
          </p>
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-ink p-4 text-sm leading-relaxed text-white">
{`cd backend
uv run python ml/train_risk.py            # risk model and its evaluation
uv run python ml/backtest_performance.py  # score model and its backtest`}
          </pre>
        </Card>
      </section>
    </div>
  );
}

function Live({ title, resolved, needed, snapshots, result }: { title: string; resolved: number; needed: number; snapshots: number; result: string | null }) {
  return (
    <div className="rounded-3xl bg-panel p-5">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{resolved}<span className="ml-2 text-base font-normal text-ink-soft">resolved of {snapshots} stored</span></p>
      <p className="mt-2 text-sm text-ink-soft">
        {result ?? `Not enough yet. A result appears once ${needed} have resolved, so a handful of students cannot mislead.`}
      </p>
    </div>
  );
}
