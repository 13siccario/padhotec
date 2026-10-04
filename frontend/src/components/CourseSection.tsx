import Link from "next/link";
import { IntervalBar } from "@/components/ui";
import type { Assessment, Course, CourseInsight, Mastery, StudySession } from "@/lib/api";
import { formatMinutes, pct, summariseTopics } from "@/lib/stats";

function masteryLabel(m: Mastery): string {
  return `Mastery ${pct(m.mean)}, likely between ${pct(m.lo)} and ${pct(m.hi)}`;
}

function MasteryCell({ m }: { m: Mastery }) {
  if (m.evidence < 1) return <span className="text-ink-soft">No evidence yet</span>;
  return (
    <span className="flex items-center gap-3">
      <IntervalBar mean={m.mean} lo={m.lo} hi={m.hi} label={masteryLabel(m)} />
      <span className="tabular-nums">
        {pct(m.mean)} <span className="text-sm text-ink-soft">({pct(m.lo)} to {pct(m.hi)})</span>
      </span>
    </span>
  );
}

export function CourseSection({
  course,
  insight,
  sessions,
  assessments,
  now,
}: {
  course: Course;
  insight: CourseInsight | undefined;
  sessions: StudySession[];
  assessments: Assessment[];
  now: Date;
}) {
  const rows = summariseTopics(course, sessions, assessments, now);
  const mastery = new Map(insight?.topics.map((t) => [t.topic_id, t.mastery]));
  const perf = insight?.performance;

  return (
    <section aria-labelledby={`course-${course.id}`}>
      <h2 id={`course-${course.id}`} className="text-xl font-semibold">
        {course.name}
      </h2>

      {perf ? (
        <div className="mt-3">
          <p className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="text-3xl font-semibold tabular-nums">{pct(perf.mean)}</span>
            <span className="text-ink-soft">
              expected score, likely between <span className="tabular-nums">{pct(perf.lo)}</span> and{" "}
              <span className="tabular-nums">{pct(perf.hi)}</span>
            </span>
          </p>
          <p className="mt-1 text-ink-soft">
            <span className="tabular-nums">{pct(perf.p_pass)}</span> chance of scoring at least{" "}
            <span className="tabular-nums">{pct(perf.pass_mark)}</span>
          </p>
          {perf.covered_weight < 1 && (
            <p className="mt-1 text-sm text-ink-soft">
              {pct(1 - perf.covered_weight)} of the exam weight has no results yet, which makes this range wider.
            </p>
          )}
        </div>
      ) : (
        insight?.performance_note && <p className="mt-3 max-w-prose text-ink-soft">{insight.performance_note}</p>
      )}

      {rows.length === 0 ? (
        <p className="mt-3 text-ink-soft">
          No topics yet.{" "}
          <Link href="/courses" className="text-blue underline">
            Add topics
          </Link>
        </p>
      ) : (
        <table className="mt-4 w-full text-left">
          <caption className="sr-only">Topics in {course.name}</caption>
          <thead>
            <tr className="border-b border-ink text-sm text-ink-soft">
              <th className="py-2 pr-4 font-medium">Topic</th>
              <th className="py-2 pr-4 font-medium">Studied, 14 days</th>
              <th className="hidden py-2 pr-4 font-medium md:table-cell">Mastery, likely range</th>
              <th className="py-2 text-right font-medium">Last score</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map(({ topic, minutes14d, lastScore }) => {
              const m = mastery.get(topic.id);
              return (
                <tr key={topic.id} className="border-b border-rule align-top">
                  <td className="py-3 pr-4 font-medium">
                    {topic.name}
                    {m && (
                      <span className="mt-2 block font-normal md:hidden">
                        <MasteryCell m={m} />
                      </span>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-ink-soft">{minutes14d > 0 ? formatMinutes(minutes14d) : "None"}</td>
                  <td className="hidden py-3 pr-4 md:table-cell">{m && <MasteryCell m={m} />}</td>
                  <td className="py-3 text-right">
                    {lastScore === null ? <span className="text-ink-soft">None</span> : pct(lastScore)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
