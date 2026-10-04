"use client";

import Link from "next/link";
import { useState } from "react";
import { ErrorNote, IntervalBar, PageHeader } from "@/components/ui";
import { api, type Career, type Skill } from "@/lib/api";
import { messageOf, useLoad } from "@/lib/hooks";
import { pct } from "@/lib/stats";
import { meshClass } from "@/lib/theme";

export default function CareerPage() {
  const skills = useLoad(api.skills);
  const careers = useLoad(api.careers);
  const [error, setError] = useState<string | null>(null);

  async function rate(key: string, rating: number | null) {
    setError(null);
    try {
      await api.rateSkill(key, rating);
      skills.reload();
      careers.reload();
    } catch (e) {
      setError(messageOf(e));
    }
  }

  const data = careers.data;

  return (
    <div className="max-w-6xl">
      <PageHeader
        title="Career"
        lead="See how close your skills are to the profile of different roles, and what to learn next."
      />
      <ErrorNote message={error ?? skills.error ?? careers.error} />
      {data && <p className="mb-6 max-w-prose rounded-2xl bg-sticky px-4 py-3 text-sm text-ink">{data.note}</p>}

      <div className="grid items-start gap-5 xl:grid-cols-2">
      {skills.data && data && (
        <SkillsSection skills={skills.data} rated={data.rated_skills} total={data.total_skills} onRate={rate} />
      )}

      {data && (
        <section aria-labelledby="roles-h" className="rounded-[28px] bg-white p-5 ring-1 ring-black/[0.04] md:p-7">
          <h2 id="roles-h" className="text-2xl font-normal">
            Roles
          </h2>
          {data.rated_skills === 0 && (
            <p className="mt-3 max-w-prose text-ink-soft">
              Nothing is rated yet, so every role shows the widest possible range. Rate a few skills above to narrow it.
            </p>
          )}
          <ul className="mt-4 space-y-3">
            {data.careers.map((c) => (
              <CareerRow key={c.key} career={c} />
            ))}
          </ul>
        </section>
      )}
      </div>
    </div>
  );
}

const OPEN_BELOW = 5;

/** Open on arrival if few skills are rated, then left alone: rating a skill must not collapse the list. */
function SkillsSection({
  skills,
  rated,
  total,
  onRate,
}: {
  skills: Skill[];
  rated: number;
  total: number;
  onRate: (key: string, rating: number | null) => void;
}) {
  const [open, setOpen] = useState(() => rated < OPEN_BELOW);
  return (
    <details open={open} onToggle={(e) => setOpen(e.currentTarget.open)} className="rounded-[28px] bg-white p-5 ring-1 ring-black/[0.04] md:p-7">
      <summary className="cursor-pointer font-display text-2xl font-normal">
        Your skills{" "}
        <span className="text-base font-normal text-ink-soft">
          ({rated} of {total} rated)
        </span>
      </summary>
      <p className="mt-3 max-w-prose text-ink-soft">
        Rate each skill from 1 (new to it) to 5 (strong). Topics you tag with a skill on the Courses page add their
        results to your rating.
      </p>
      <ul className="mt-3 divide-y divide-line">
        {skills.map((s) => (
          <SkillRow key={s.key} skill={s} onRate={onRate} />
        ))}
      </ul>
    </details>
  );
}

function SkillRow({ skill, onRate }: { skill: Skill; onRate: (key: string, rating: number | null) => void }) {
  return (
    <li className="grid gap-x-4 gap-y-2 py-3 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="font-medium">{skill.label}</p>
        {skill.topics.length > 0 && <p className="text-sm text-ink-soft">From your topics: {skill.topics.join(", ")}</p>}
        {skill.level && (
          <span className="mt-1 flex items-center gap-3 text-sm text-ink-soft">
            <IntervalBar
              mean={skill.level.mean / 100}
              lo={skill.level.lo / 100}
              hi={skill.level.hi / 100}
              label={`Estimated level ${Math.round(skill.level.mean)} of 100, likely between ${Math.round(skill.level.lo)} and ${Math.round(skill.level.hi)}`}
            />
            {Math.round(skill.level.mean)} ({Math.round(skill.level.lo)} to {Math.round(skill.level.hi)})
          </span>
        )}
      </div>
      <div role="group" aria-label={`Rate ${skill.label}`} className="flex gap-1.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={skill.rating === n}
            onClick={() => onRate(skill.key, skill.rating === n ? null : n)}
            className={`size-9 rounded-full border text-base transition-colors ${
              skill.rating === n ? "border-ink bg-ink font-medium text-white" : "border-line bg-white hover:border-ink"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </li>
  );
}

function readinessText(c: Career): string {
  return c.readiness_hi - c.readiness_lo < 0.05 ? pct(c.readiness_mean) : `${pct(c.readiness_lo)} to ${pct(c.readiness_hi)}`;
}

function CareerRow({ career: c }: { career: Career }) {
  const text = readinessText(c);
  return (
    <li>
      <details className="group rounded-3xl bg-panel p-4">
        <summary className="grid cursor-pointer gap-x-6 gap-y-3 sm:grid-cols-[1fr_auto] sm:items-center">
          <span className="flex items-center gap-3">
            <span aria-hidden="true" className={`mesh ${meshClass(c.key.length * 7 + c.key.charCodeAt(0))} size-11 shrink-0 rounded-2xl`} />
            <span>
              <span className="font-medium">{c.label}</span>
              <span className="block text-sm text-ink-soft">{c.summary}</span>
            </span>
          </span>
          <span className="flex items-center gap-3 tabular-nums">
            <IntervalBar
              mean={c.readiness_mean}
              lo={c.readiness_lo}
              hi={c.readiness_hi}
              label={`Readiness for ${c.label}: ${text}`}
            />
            <span className="w-24 text-right">{text}</span>
          </span>
        </summary>

        <div className="mt-5 space-y-6 rounded-2xl bg-white p-4">
          {c.unrated > 0 && (
            <p className="text-sm text-ink-soft">
              {c.unrated} of {c.total} skills for this role are not rated yet, which is why the range is wide.
            </p>
          )}

          {c.roadmap.length === 0 ? (
            <p>You meet every skill in this role&apos;s profile.</p>
          ) : (
            <div>
              <h3 className="font-display text-xl font-normal">Roadmap</h3>
              <ol className="mt-2 space-y-3">
                {c.roadmap.map((step, i) => (
                  <li key={step.skill} className="grid grid-cols-[1.5rem_1fr] gap-x-2">
                    <span className="text-ink-soft">{i + 1}.</span>
                    <span>
                      <span className="font-medium">{step.label}</span>
                      <span className="ml-2 text-sm text-ink-soft">
                        {step.current === null ? "not rated" : `now ${Math.round(step.current)}`}, aim for{" "}
                        {Math.round(step.target)}
                      </span>
                      <span className="block text-sm text-ink-soft">{step.reason}</span>
                      <span className="block text-sm">
                        {step.your_topics.length > 0 ? (
                          <>You already track: {step.your_topics.join(", ")}. Keep logging practice.</>
                        ) : (
                          <>
                            No topic builds this yet.{" "}
                            <Link href="/courses" className="font-medium text-ink underline">
                              Add one and tag it
                            </Link>
                          </>
                        )}
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </details>
    </li>
  );
}
