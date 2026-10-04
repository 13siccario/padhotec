"use client";

import { useState } from "react";

/*
 * Charts for the evidence page. Hand-built so they follow the rules exactly:
 * thin marks, a 2px surface ring on dots, hairline solid grid, selective direct labels, text in text tokens
 * (never the data colour), a hover and keyboard tooltip with the value leading, and a table twin for every chart.
 * Emphasis, not categorical: the thing being judged is ink, everything it is compared with is grey.
 */

const INK = "#111111";
const MUTED = "#8e8882"; // de-emphasis grey, 3.5:1 on white
const GRID = "rgba(17,17,17,0.12)";
const SURFACE = "#ffffff";
const TEXT_SOFT = "#5f5953";

export type TableView = { head: string[]; rows: (string | number)[][] };

export function ChartCard({
  title,
  subtitle,
  children,
  table,
  wide,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  table: TableView;
  wide?: boolean;
}) {
  return (
    <figure className={`min-w-0 rounded-[28px] bg-white p-5 ring-1 ring-black/[0.04] md:p-7 ${wide ? "lg:col-span-2" : ""}`}>
      <figcaption>
        <h3 className="font-sans text-xl font-medium tracking-normal">{title}</h3>
        {subtitle && <p className="mt-1 max-w-prose text-sm text-ink-soft">{subtitle}</p>}
      </figcaption>
      <div className="mt-5">{children}</div>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer text-ink-soft underline">Table view</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[20rem] text-left tabular-nums">
            <thead>
              <tr className="border-b border-line text-ink-soft">
                {table.head.map((h) => (
                  <th key={h} className="py-1.5 pr-4 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((r, i) => (
                <tr key={i} className="border-b border-line/60 last:border-0">
                  {r.map((c, j) => (
                    <td key={j} className="py-1.5 pr-4">
                      {c}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** One big number with its range. Proportional figures: tabular digits look loose at this size. */
export function Stat({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: string }) {
  return (
    <div className={`rounded-[28px] p-5 md:p-6 ${tone}`}>
      <p className="text-sm text-ink">{label}</p>
      <p className="mt-2 font-sans text-5xl font-semibold leading-none tracking-tight text-ink">{value}</p>
      <p className="mt-3 text-sm text-ink">{sub}</p>
    </div>
  );
}

function Tooltip({ title, value, detail, className = "" }: { title: string; value: string; detail?: string; className?: string }) {
  return (
    <span
      role="presentation"
      className={`pointer-events-none absolute z-10 w-max max-w-[16rem] rounded-2xl bg-ink px-3 py-2 text-left text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus:opacity-100 ${className}`}
    >
      <span className="block text-base font-semibold leading-tight">{value}</span>
      <span className="block text-white/80">{title}</span>
      {detail && <span className="block text-white/80">{detail}</span>}
    </span>
  );
}

/* ---- Dot plot: estimates on a shared axis, optionally with a 95% interval ------------------------------- */

export type DotRow = {
  label: string;
  value: number;
  ci?: [number, number] | null;
  highlight?: boolean;
  note?: string;
};

export function DotPlot({
  rows,
  domain,
  ticks,
  format,
  tickFormat,
  reference,
  ariaLabel,
}: {
  rows: DotRow[];
  domain: [number, number];
  ticks: number[];
  format: (v: number) => string;
  tickFormat?: (v: number) => string;
  reference?: { value: number; label: string };
  ariaLabel: string;
}) {
  const tick = tickFormat ?? format;
  const pos = (v: number) => `${((Math.min(Math.max(v, domain[0]), domain[1]) - domain[0]) / (domain[1] - domain[0])) * 100}%`;
  return (
    <div role="group" aria-label={ariaLabel}>
      <ul>
        {rows.map((r) => {
          const color = r.highlight ? INK : MUTED;
          return (
            <li key={r.label} tabIndex={0} className="group relative flex flex-col rounded-xl py-1.5 outline-offset-0 focus-visible:bg-panel md:flex-row md:items-center">
              <span className={`shrink-0 pr-3 text-sm md:w-48 ${r.highlight ? "font-medium text-ink" : "text-ink-soft"}`}>
                {r.label}
              </span>
              <span className="relative mr-14 h-8 min-w-0 md:mr-16 md:flex-1">
                <span className="absolute inset-x-0 top-1/2 h-px" style={{ background: GRID }} />
                {reference && (
                  <span className="absolute inset-y-0 w-px" style={{ left: pos(reference.value), background: INK, opacity: 0.55 }} />
                )}
                {r.ci && (
                  <>
                    <span className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full" style={{ left: pos(r.ci[0]), width: `calc(${pos(r.ci[1])} - ${pos(r.ci[0])})`, background: color }} />
                    {r.ci.map((c) => (
                      <span key={c} className="absolute top-1/2 h-3 w-0.5 -translate-x-1/2 -translate-y-1/2" style={{ left: pos(c), background: color }} />
                    ))}
                  </>
                )}
                <span
                  className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{ left: pos(r.value), background: color, boxShadow: `0 0 0 2px ${SURFACE}` }}
                />
                <span
                  className="absolute top-1/2 -translate-y-1/2 pl-3 text-sm tabular-nums"
                  style={{ left: pos(r.ci ? r.ci[1] : r.value), color: INK }}
                >
                  {format(r.value)}
                </span>
              </span>
              <Tooltip
                title={r.label}
                value={format(r.value)}
                detail={r.ci ? `95% interval ${format(r.ci[0])} to ${format(r.ci[1])}` : r.note}
                className="right-0 top-0 -translate-y-full"
              />
            </li>
          );
        })}
      </ul>
      <div className="flex">
        <span className="hidden shrink-0 md:block md:w-48" />
        <span className="relative mr-14 h-5 min-w-0 flex-1 md:mr-16">
          {ticks.map((t) => (
            <span key={t} className="absolute top-1 -translate-x-1/2 text-xs tabular-nums text-ink-soft" style={{ left: pos(t) }}>
              {tick(t)}
            </span>
          ))}
        </span>
      </div>
      {reference && (
        <p className="mt-2 flex items-center gap-2 text-xs text-ink-soft">
          <span className="inline-block h-3 w-px" style={{ background: INK, opacity: 0.55 }} aria-hidden="true" />
          {reference.label}
        </p>
      )}
    </div>
  );
}

/* ---- Columns: a few ordered categories, with a reference line ------------------------------------------- */

export function Columns({
  items,
  format,
  reference,
  ariaLabel,
}: {
  items: { label: string; value: number; detail?: string }[];
  format: (v: number) => string;
  reference?: { value: number; label: string };
  ariaLabel: string;
}) {
  const max = Math.max(...items.map((i) => i.value), reference?.value ?? 0) * 1.25;
  const h = (v: number) => `${(v / max) * 100}%`;
  return (
    <div role="group" aria-label={ariaLabel}>
      <div className="relative flex h-44 items-end justify-around border-b" style={{ borderColor: GRID }}>
        {reference && (
          <span className="absolute inset-x-0 h-px" style={{ bottom: h(reference.value), background: INK, opacity: 0.55 }}>
            <span className="absolute -top-5 left-0 text-xs text-ink-soft">{reference.label}</span>
          </span>
        )}
        {items.map((it) => (
          <div key={it.label} tabIndex={0} className="group relative flex h-full w-24 flex-col items-center justify-end rounded-xl outline-offset-0 focus-visible:bg-panel">
            <span className="mb-1 text-sm font-medium tabular-nums text-ink">{format(it.value)}</span>
            <span className="w-6 rounded-t" style={{ height: h(it.value), background: INK, minHeight: 2 }} />
            <Tooltip title={it.label} value={format(it.value)} detail={it.detail} className="left-1/2 top-2 -translate-x-1/2" />
          </div>
        ))}
      </div>
      <div className="flex justify-around pt-2">
        {items.map((it) => (
          <span key={it.label} className="w-24 text-center text-sm text-ink-soft">
            {it.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---- SVG scales shared by the scatter and line charts --------------------------------------------------- */

const W = 420;
const H = 300;
const M = { l: 50, r: 14, t: 16, b: 46 };

function scale(domain: [number, number], range: [number, number]) {
  return (v: number) => range[0] + ((v - domain[0]) / (domain[1] - domain[0])) * (range[1] - range[0]);
}

function Axes({
  x,
  y,
  xTicks,
  yTicks,
  xFormat,
  yFormat,
  xLabel,
  yLabel,
}: {
  x: (v: number) => number;
  y: (v: number) => number;
  xTicks: number[];
  yTicks: number[];
  xFormat: (v: number) => string;
  yFormat: (v: number) => string;
  xLabel: string;
  yLabel: string;
}) {
  return (
    <g fontSize={13} fill={TEXT_SOFT}>
      {yTicks.map((t) => (
        <g key={`y${t}`}>
          <line x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth={1} />
          <text x={M.l - 8} y={y(t) + 4} textAnchor="end">
            {yFormat(t)}
          </text>
        </g>
      ))}
      {xTicks.map((t) => (
        <text key={`x${t}`} x={x(t)} y={H - M.b + 18} textAnchor="middle">
          {xFormat(t)}
        </text>
      ))}
      <text x={(M.l + W - M.r) / 2} y={H - 6} textAnchor="middle">
        {xLabel}
      </text>
      <text transform={`translate(14 ${(M.t + H - M.b) / 2}) rotate(-90)`} textAnchor="middle">
        {yLabel}
      </text>
    </g>
  );
}

/** Position a tooltip over an SVG point, as a percentage of the viewBox so it follows the responsive size. */
function overSvg(px: number, py: number) {
  return { left: `${(px / W) * 100}%`, top: `${(py / H) * 100}%` };
}

/* ---- Reliability: predicted against observed, with the line of perfect agreement -------------------------- */

export function Reliability({
  points,
  max,
  ariaLabel,
}: {
  points: { predicted: number; observed: number; n: number }[];
  max: number;
  ariaLabel: string;
}) {
  const [active, setActive] = useState<number | null>(null);
  const x = scale([0, max], [M.l, W - M.r]);
  const y = scale([0, max], [H - M.b, M.t]);
  const ticks = Array.from({ length: Math.round(max / 0.02) + 1 }, (_, i) => i * 0.02);
  const pct = (v: number) => `${(v * 100).toFixed(v < 0.1 ? 1 : 0)}%`;
  const tip = active === null ? null : points[active];
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="group" aria-label={ariaLabel}>
        <Axes x={x} y={y} xTicks={ticks} yTicks={ticks} xFormat={pct} yFormat={pct} xLabel="Predicted chance of stopping" yLabel="Observed rate" />
        <line x1={x(0)} y1={y(0)} x2={x(max)} y2={y(max)} stroke={INK} strokeOpacity={0.55} strokeWidth={1} />
        <text x={x(max) - 6} y={y(max) + 16} textAnchor="end" fontSize={13} fill={TEXT_SOFT}>
          Perfect agreement
        </text>
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={x(p.predicted)} cy={y(p.observed)} r={5} fill={INK} stroke={SURFACE} strokeWidth={2} />
            <circle
              cx={x(p.predicted)}
              cy={y(p.observed)}
              r={14}
              fill="transparent"
              tabIndex={0}
              role="img"
              aria-label={`Predicted ${pct(p.predicted)}, observed ${pct(p.observed)}, ${p.n.toLocaleString()} rows`}
              onPointerEnter={() => setActive(i)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(i)}
              onBlur={() => setActive(null)}
              style={{ outline: "none" }}
            />
          </g>
        ))}
      </svg>
      {tip && (
        <span
          role="presentation"
          className="pointer-events-none absolute z-10 w-max -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-2xl bg-ink px-3 py-2 text-xs text-white shadow-lg"
          style={overSvg(x(tip.predicted), y(tip.observed))}
        >
          <span className="block text-base font-semibold leading-tight">{pct(tip.observed)} observed</span>
          <span className="block text-white/80">{pct(tip.predicted)} predicted</span>
          <span className="block text-white/80">{tip.n.toLocaleString()} rows in this group</span>
        </span>
      )}
    </div>
  );
}

/* ---- Line: one measure against a setting, with the chosen value marked ------------------------------------ */

export function LineChart({
  points,
  xDomain,
  yDomain,
  xTicks,
  yTicks,
  xFormat,
  yFormat,
  xLabel,
  yLabel,
  chosen,
  reference,
  ariaLabel,
}: {
  points: { x: number; y: number }[];
  xDomain: [number, number];
  yDomain: [number, number];
  xTicks: number[];
  yTicks: number[];
  xFormat: (v: number) => string;
  yFormat: (v: number) => string;
  xLabel: string;
  yLabel: string;
  chosen?: number;
  reference?: { y: number; label: string };
  ariaLabel: string;
}) {
  const [active, setActive] = useState<number | null>(null);
  const x = scale(xDomain, [M.l, W - M.r]);
  const y = scale(yDomain, [H - M.b, M.t]);
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.x)} ${y(p.y)}`).join(" ");
  const tip = active === null ? null : points[active];
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="group" aria-label={ariaLabel}>
        <Axes x={x} y={y} xTicks={xTicks} yTicks={yTicks} xFormat={xFormat} yFormat={yFormat} xLabel={xLabel} yLabel={yLabel} />
        {reference && (
          <g>
            <line x1={M.l} x2={W - M.r} y1={y(reference.y)} y2={y(reference.y)} stroke={INK} strokeOpacity={0.55} strokeWidth={1} />
            <text x={W - M.r - 4} y={y(reference.y) - 6} textAnchor="end" fontSize={13} fill={TEXT_SOFT}>
              {reference.label}
            </text>
          </g>
        )}
        {tip && <line x1={x(tip.x)} x2={x(tip.x)} y1={M.t} y2={H - M.b} stroke={INK} strokeOpacity={0.35} strokeWidth={1} />}
        <path d={d} fill="none" stroke={INK} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={x(p.x)} cy={y(p.y)} r={p.x === chosen ? 6 : 4.5} fill={p.x === chosen ? INK : SURFACE} stroke={p.x === chosen ? SURFACE : INK} strokeWidth={2} />
            {p.x === chosen && (
              <text x={x(p.x)} y={y(p.y) - 14} textAnchor="middle" fontSize={13} fill={TEXT_SOFT}>
                chosen
              </text>
            )}
            <rect
              x={x(p.x) - 16}
              y={M.t}
              width={32}
              height={H - M.t - M.b}
              fill="transparent"
              tabIndex={0}
              role="img"
              aria-label={`${xFormat(p.x)}: ${yFormat(p.y)}`}
              onPointerEnter={() => setActive(i)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(i)}
              onBlur={() => setActive(null)}
              style={{ outline: "none" }}
            />
          </g>
        ))}
      </svg>
      {tip && (
        <span
          role="presentation"
          className="pointer-events-none absolute z-10 w-max -translate-x-1/2 -translate-y-[calc(100%+14px)] rounded-2xl bg-ink px-3 py-2 text-xs text-white shadow-lg"
          style={overSvg(x(tip.x), y(tip.y))}
        >
          <span className="block text-base font-semibold leading-tight">{yFormat(tip.y)}</span>
          <span className="block text-white/80">{xLabel}: {xFormat(tip.x)}</span>
        </span>
      )}
    </div>
  );
}
