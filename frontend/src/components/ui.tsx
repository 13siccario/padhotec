"use client";

import { useState } from "react";

export const inputCls =
  "w-full rounded-sm border border-rule bg-white px-3 py-2 text-base text-ink placeholder:text-ink-soft/60 focus-visible:border-blue";

export function PageHeader({ title, lead }: { title: string; lead?: string }) {
  return (
    <header className="mb-8">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">{title}</h1>
      {lead && <p className="mt-2 max-w-prose text-ink-soft">{lead}</p>}
    </header>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-ink">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-sm text-ink-soft">{hint}</span>}
    </label>
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "quiet" | "danger" };

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  const styles = {
    primary: "bg-blue text-white hover:bg-blue-deep",
    quiet: "border border-rule bg-white text-ink hover:border-ink",
    danger: "border border-red text-red hover:bg-red hover:text-white",
  }[variant];
  return (
    <button
      {...props}
      className={`rounded-sm px-4 py-2 text-base font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

export function ErrorNote({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-sm border border-red/40 bg-red/5 px-3 py-2 text-sm text-red">
      {message}
    </p>
  );
}

export function SuccessNote({ children }: { children: React.ReactNode }) {
  return (
    <p role="status" className="rounded-sm border border-green/40 bg-green/5 px-3 py-2 text-sm text-green">
      {children}
    </p>
  );
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
      <button onClick={() => setArmed(true)} className="text-sm text-ink-soft underline hover:text-red">
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
        className="font-medium text-red underline"
      >
        {confirmLabel}
      </button>
      <button onClick={() => setArmed(false)} className="text-ink-soft underline">
        Keep
      </button>
    </span>
  );
}

/**
 * The app's signature mark: a segment on a 1-5 track. In Phase 3 the same bar
 * will show a mastery credible interval instead of a self-rating.
 */
export function RangeBar({ from, to }: { from: number | null; to: number | null }) {
  const a = from ?? to;
  const b = to ?? from;
  if (a === null || b === null) return null;
  const pos = (v: number) => ((v - 1) / 4) * 100;
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  const label =
    from !== null && to !== null && from !== to
      ? `Confidence moved from ${from} to ${to} out of 5`
      : `Confidence ${b} out of 5`;
  return (
    <span role="img" aria-label={label} className="relative block h-4 w-36">
      <span className="absolute inset-x-0 top-1/2 h-px bg-rule" />
      {[0, 25, 50, 75, 100].map((p) => (
        <span key={p} className="absolute top-1/2 h-2 w-px -translate-y-1/2 bg-rule" style={{ left: `${p}%` }} />
      ))}
      <span
        className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-blue/35"
        style={{ left: `${pos(lo)}%`, width: `${Math.max(pos(hi) - pos(lo), 0)}%` }}
      />
      <span
        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue ring-2 ring-paper"
        style={{ left: `${pos(b)}%` }}
      />
    </span>
  );
}

/** A 0-100% track with the likely range as a band and the best estimate as a dot. */
export function IntervalBar({ mean, lo, hi, label }: { mean: number; lo: number; hi: number; label: string }) {
  const pos = (v: number) => `${Math.min(Math.max(v, 0), 1) * 100}%`;
  return (
    <span role="img" aria-label={label} className="relative block h-4 w-36">
      <span className="absolute inset-x-0 top-1/2 h-px bg-rule" />
      {[0, 25, 50, 75, 100].map((p) => (
        <span key={p} className="absolute top-1/2 h-2 w-px -translate-y-1/2 bg-rule" style={{ left: `${p}%` }} />
      ))}
      <span
        className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-blue/35"
        style={{ left: pos(lo), width: `calc(${pos(hi)} - ${pos(lo)})` }}
      />
      <span
        className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue ring-2 ring-paper"
        style={{ left: pos(mean) }}
      />
    </span>
  );
}
