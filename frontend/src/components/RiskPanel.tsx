import Link from "next/link";
import { Card, SectionTitle, btnPrimary } from "@/components/ui";
import type { Risk } from "@/lib/api";
import { pct1 } from "@/lib/stats";

const LEVEL = {
  low: { word: "Low", tone: "bg-mint" },
  elevated: { word: "Elevated", tone: "bg-sticky" },
  high: { word: "High", tone: "bg-peach" },
} as const;

export function RiskPanel({ risk }: { risk: Risk }) {
  const level = risk.level ? LEVEL[risk.level] : null;
  return (
    <Card aria-labelledby="risk-h" className="h-full">
      <SectionTitle id="risk-h">Staying on track</SectionTitle>

      {risk.status !== "ok" || risk.probability === null || level === null ? (
        <p className="mt-4 max-w-prose text-ink-soft">{risk.message}</p>
      ) : (
        <>
          <p className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className={`rounded-full px-5 py-1.5 font-display text-3xl font-normal ${level.tone}`}>
              {level.word}
            </span>
            <span className="text-ink-soft">
              {pct1(risk.probability)} estimated chance of stopping within {risk.horizon_days} days
              {risk.typical !== null && <>, against {pct1(risk.typical)} for the average student in the data</>}
            </span>
          </p>

          {risk.drivers.length > 0 && (
            <ul className="mt-5 space-y-2">
              {risk.drivers.map((d) => (
                <li key={d.label} className="flex items-start gap-3 rounded-2xl bg-panel px-4 py-3">
                  <span
                    className={`mt-0.5 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      d.effect === "raises" ? "bg-peach text-warn" : "bg-mint text-ok"
                    }`}
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
            <p className="mt-5 flex flex-wrap items-center gap-3">
              <span>Studying on more days is the part you control.</span>
              <Link href="/log" className={btnPrimary}>
                Log a session
              </Link>
            </p>
          )}
        </>
      )}

      <p className="mt-5 max-w-prose text-sm text-ink-soft">
        Experimental. This estimate comes from patterns in a public university dataset (OULAD), not from Padhotec
        students yet. Treat it as a prompt to check in with yourself, not a verdict. Only you can see it.
      </p>
    </Card>
  );
}
