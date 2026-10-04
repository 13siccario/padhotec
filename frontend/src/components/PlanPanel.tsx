"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, SectionTitle, btnPrimary } from "@/components/ui";
import { api, type Plan } from "@/lib/api";
import { messageOf } from "@/lib/hooks";

const CHOICES = [30, 45, 60, 90, 120];

export function PlanPanel() {
  // null means "use my usual daily time from my profile".
  const [minutes, setMinutes] = useState<number | null>(null);
  const [state, setState] = useState<{ plan?: Plan; error?: string }>({});

  useEffect(() => {
    let alive = true;
    api.plan(minutes).then(
      (plan) => alive && setState({ plan }),
      (e) => alive && setState({ error: messageOf(e) }),
    );
    return () => {
      alive = false;
    };
  }, [minutes]);

  const { plan, error } = state;

  return (
    <Card aria-labelledby="plan-h" className="h-full">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle id="plan-h" count={plan?.blocks.length} tone="bg-sticky">
          Today
        </SectionTitle>
        {plan && (
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Time available
            <select
              value={minutes ?? ""}
              onChange={(e) => setMinutes(e.target.value ? Number(e.target.value) : null)}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-ink"
            >
              <option value="">Usual ({plan.budget_minutes} min)</option>
              {CHOICES.map((m) => (
                <option key={m} value={m}>
                  {m} min
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-4 text-bad">
          {error}
        </p>
      )}
      {!plan && !error && <p className="mt-4 text-ink-soft">Building your plan</p>}

      {plan && (
        <>
          <p className="mt-5 max-w-prose font-display text-3xl font-normal leading-snug tracking-tight">
            {plan.headline}
          </p>

          {plan.blocks.length > 0 && (
            <ol className="mt-6 space-y-3">
              {plan.blocks.map((b) => (
                <li key={b.topic_id} className="grid grid-cols-[4.75rem_1fr] gap-4 rounded-3xl bg-panel p-3.5">
                  <span
                    className={`flex h-[4.75rem] flex-col items-center justify-center rounded-2xl text-center ${
                      b.kind === "diagnose" ? "bg-lilac" : "bg-sticky"
                    }`}
                  >
                    <span className="font-display text-3xl font-semibold leading-none">{b.minutes}</span>
                    <span className="mt-1 text-xs">min</span>
                  </span>
                  <span className="py-0.5">
                    <span className="font-medium">{b.topic_name}</span>
                    <span className="ml-2 text-sm text-ink-soft">
                      {b.course_name}, {b.kind === "diagnose" ? "self-test" : "practice"}
                    </span>
                    <span className="mt-1 block text-ink-soft">{b.reason}</span>
                  </span>
                </li>
              ))}
            </ol>
          )}

          <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
            <p className="max-w-md text-sm text-ink-soft">
              {plan.studied_today > 0 ? `${plan.studied_today} of ${plan.budget_minutes} min done today. ` : ""}
              {plan.note}
            </p>
            {plan.blocks.length > 0 && (
              <Link href="/log" className={btnPrimary}>
                Log what you did
              </Link>
            )}
          </div>
        </>
      )}
    </Card>
  );
}
