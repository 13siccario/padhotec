"use client";

import { useState } from "react";

export const inputCls =
  "w-full rounded-2xl border border-line bg-white px-4 py-2.5 text-base text-ink placeholder:text-ink-soft/60 focus-visible:border-ink";

/** Class strings so links can look like buttons without wrapping a button in a link. */
export const btnPrimary =
  "inline-flex items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 text-base font-medium text-white transition-colors hover:bg-black/75";
export const btnQuiet =
  "inline-flex items-center justify-center gap-2 rounded-full border border-ink px-5 py-2.5 text-base font-medium text-ink transition-colors hover:bg-white";

/** The white rounded surface everything sits on. */
export function Card({
  children,
  className = "",
  as: Tag = "section",
  ...rest
}: React.HTMLAttributes<HTMLElement> & { as?: "section" | "div" | "article" }) {
  return (
    <Tag className={`rounded-[28px] bg-white p-5 ring-1 ring-black/[0.04] md:p-7 ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

/** A darker nested panel, for groups of tiles inside the page. */
export function Panel({ children, className = "", ...rest }: React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={`rounded-[28px] bg-panel p-4 md:p-5 ${className}`} {...rest}>
      {children}
    </section>
  );
}

/** A title with a small count beside it, as in "Courses 3". */
export function SectionTitle({
  id,
  children,
  count,
  tone = "bg-sticky",
}: {
  id?: string;
  children: React.ReactNode;
  count?: number;
  tone?: string;
}) {
  return (
    <h2 id={id} className="flex items-center gap-2.5 text-2xl font-normal">
      {children}
      {count !== undefined && (
        <span className={`rounded-full px-2.5 py-0.5 text-sm font-medium ${tone}`}>{count}</span>
      )}
    </h2>
  );
}

/** Two-tone heading: the subject in black, the explanation in grey, as one thought. */
export function PageHeader({ title, lead }: { title: string; lead?: string }) {
  return (
    <header className="mb-8 max-w-2xl">
      <h1 className="text-4xl font-normal leading-tight md:text-5xl">{title}</h1>
      {lead && <p className="mt-2 text-xl leading-snug text-ink-soft md:text-2xl md:text-ink-mute">{lead}</p>}
    </header>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-sm text-ink-soft">{hint}</span>}
    </label>
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "quiet" | "danger" };

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  const styles = {
    primary: btnPrimary,
    quiet: btnQuiet,
    danger:
      "inline-flex items-center justify-center rounded-full border border-bad px-5 py-2.5 text-base font-medium text-bad transition-colors hover:bg-bad hover:text-white",
  }[variant];
  return <button {...props} className={`${styles} disabled:cursor-not-allowed disabled:opacity-50 ${className}`} />;
}

export function ErrorNote({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-2xl bg-[#fde6e2] px-4 py-3 text-sm text-bad">
      {message}
    </p>
  );
}

export function SuccessNote({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-2xl bg-mint px-4 py-3 text-sm text-ok">
      {children}
    </p>
  );
}

/** A small rounded label. Sentence case, and always words, so meaning never rests on colour alone. */
export function Chip({ children, tone = "bg-panel" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`inline-block rounded-full px-3 py-1 text-sm font-medium text-ink ${tone}`}>{children}</span>;
}

/** Two-step delete so a stray click can't remove data. */
export function ConfirmButton({
  label,
  confirmLabel,
  onConfirm,
}: {
  label: string;
  confirmLabel: string;
  onConfirm: () => void | Promise<void>;
}) {
  const [armed, setArmed] = useState(false);
  if (!armed) {
    return (
      <button onClick={() => setArmed(true)} className="text-sm text-ink-soft underline hover:text-bad">
        {label}
      </button>
    );
  }
  return (
    <span className="inline-flex items-center gap-3 text-sm">
      <button
        onClick={async () => {
          await onConfirm();
          setArmed(false);
        }}
        className="rounded-full bg-bad px-3 py-1 font-medium text-white"
      >
        {confirmLabel}
      </button>
      <button onClick={() => setArmed(false)} className="text-ink-soft underline">
        Keep
      </button>
    </span>
  );
}

/** A thin rounded progress bar. Pair it with the number it shows. */
export function ProgressBar({ fraction, barClass = "bg-ink" }: { fraction: number; barClass?: string }) {
  const w = `${Math.min(Math.max(fraction, 0), 1) * 100}%`;
  return (
    <span aria-hidden="true" className="block h-1.5 w-full overflow-hidden rounded-full bg-black/[0.07]">
      <span className={`block h-full rounded-full ${barClass}`} style={{ width: w }} />
    </span>
  );
}

const TICKS = [0, 25, 50, 75, 100];

/**
 * The app's signature mark: a likely range as a soft band and a best estimate as a dot, on a track.
 * Optionally a diamond for "you". All positions are fractions of the track (0 to 1).
 */
export function IntervalBar({
  mean,
  lo,
  hi,
  label,
  marker,
  width = "w-36",
}: {
  mean: number;
  lo: number;
  hi: number;
  label: string;
  marker?: number | null;
  width?: string;
}) {
  const pos = (v: number) => `${Math.min(Math.max(v, 0), 1) * 100}%`;
  return (
    <span role="img" aria-label={label} className={`relative block h-5 ${width}`}>
      <span className="absolute inset-x-0 top-1/2 h-px bg-black/15" />
      {TICKS.map((p) => (
        <span key={p} className="absolute top-1/2 h-2 w-px -translate-y-1/2 bg-black/15" style={{ left: `${p}%` }} />
      ))}
      <span
        className="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-full bg-gradient-to-r from-[#f3dc4a] to-[#d9c4f2] ring-1 ring-black/10"
        style={{ left: pos(lo), width: `calc(${pos(hi)} - ${pos(lo)})` }}
      />
      <span
        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-ink ring-2 ring-white"
        style={{ left: pos(mean) }}
      />
      {marker !== null && marker !== undefined && (
        <span
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rotate-45 border-[1.5px] border-ink bg-yellow"
          style={{ left: pos(marker) }}
        />
      )}
    </span>
  );
}

/** Confidence moving from one rating to another on a 1-5 track. */
export function RangeBar({ from, to }: { from: number | null; to: number | null }) {
  const a = from ?? to;
  const b = to ?? from;
  if (a === null || b === null) return null;
  const pos = (v: number) => (v - 1) / 4;
  const label =
    from !== null && to !== null && from !== to
      ? `Confidence moved from ${from} to ${to} out of 5`
      : `Confidence ${b} out of 5`;
  return <IntervalBar mean={pos(b)} lo={pos(Math.min(a, b))} hi={pos(Math.max(a, b))} label={label} />;
}
