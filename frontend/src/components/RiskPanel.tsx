import Link from "next/link";
import type { Risk } from "@/lib/api";
import { pct1 } from "@/lib/stats";

const LEVEL_WORD = { low: "Low", elevated: "Elevated", high: "High" } as const;

export function RiskPanel({ risk }: { risk: Risk }) {
  return (
    <section aria-labelledby="risk-h">
      <h2 id="risk-h" className="text-xl font-semibold">
        Staying on track
      </h2>

      {risk.status !== "ok" || risk.probability === null || risk.level === null ? (
        <p className="mt-3 max-w-prose text-ink-soft">{risk.message}</p>
      ) : (
        <>
          <p className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="text-3xl font-semibold">{LEVEL_WORD[risk.level]}</span>
            <span className="text-ink-soft">
              {pct1(risk.probability)} estimated chance of stopping within{" "}
              {risk.horizon_days} days
              {risk.typical !== null && (
                <>
                  , against {pct1(risk.typical)} for the average student in the
                  data
                </>
              )}
            </span>
          </p>

          {risk.drivers.length > 0 && (
            <ul className="mt-4 divide-y divide-rule border-y border-rule">
              {risk.drivers.map((d) => (
                <li key={d.label} className="flex items-baseline gap-4 py-3">
                  <span
                    className={`w-24 shrink-0 text-sm font-medium ${d.effect === "raises" ? "text-amber" : "text-green"}`}
                  >
                    {d.effect === "raises" ? "Raises risk" : "Lowers risk"}
                  </span>
                  <span>
                    <span className="font-medium">{d.label}.</span> {d.detail}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {risk.level !== "low" && (
            <p className="mt-4">
              Studying on more days is the part you control.{" "}
              <Link href="/log" className="text-blue underline">
                Log a session
              </Link>
            </p>
          )}
        </>
      )}

      <p className="mt-4 max-w-prose text-sm text-ink-soft">
        Experimental. This estimate comes from patterns in a public university dataset (OULAD), not from Padhotec
        students yet. Treat it as a prompt to check in with yourself, not a verdict. Only you can see it.
      </p>
    </section>
  );
}
