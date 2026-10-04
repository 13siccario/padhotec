"use client";

import { useState } from "react";
import { Button, ConfirmButton, ErrorNote, Field, PageHeader, SuccessNote, inputCls } from "@/components/ui";
import { api, tokenStore, type Profile } from "@/lib/api";
import { messageOf, useLoad } from "@/lib/hooks";

const GOALS = [
  ["", "Not set"],
  ["exam", "Pass or ace an exam"],
  ["course", "Finish a course"],
  ["internship", "Get an internship"],
  ["job", "Get a job"],
  ["higher_studies", "Higher studies"],
  ["career_change", "Change careers"],
] as const;

export default function ProfilePage() {
  const { data, error, loading } = useLoad(api.profile);

  return (
    <div className="max-w-xl">
      <PageHeader title="Profile" lead="Your goal and weekly hours shape the plans Padhotec builds for you." />
      <ErrorNote message={error} />
      {loading && <p className="text-ink-soft">Loading</p>}
      {data && <ProfileForm initial={data} />}
      <DataControls />
    </div>
  );
}

function ProfileForm({ initial }: { initial: Profile }) {
  const [p, setP] = useState<Profile>(initial);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setSaved(false);
    setP((prev) => ({ ...prev, [key]: value }));
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setP(await api.saveProfile(p));
      setSaved(true);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <Field label="Name">
        <input value={p.display_name} onChange={(e) => set("display_name", e.target.value)} className={inputCls} />
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Institution">
          <input value={p.institution} onChange={(e) => set("institution", e.target.value)} className={inputCls} />
        </Field>
        <Field label="Degree">
          <input value={p.degree} onChange={(e) => set("degree", e.target.value)} className={inputCls} />
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Year of study">
          <input
            type="number"
            min={1}
            max={10}
            value={p.year ?? ""}
            onChange={(e) => set("year", e.target.value ? Number(e.target.value) : null)}
            className={inputCls}
          />
        </Field>
        <Field label="Study hours per week">
          <input
            type="number"
            min={0}
            max={100}
            step="0.5"
            value={p.weekly_study_hours ?? ""}
            onChange={(e) => set("weekly_study_hours", e.target.value ? Number(e.target.value) : null)}
            className={inputCls}
          />
        </Field>
      </div>
      <Field label="Main goal">
        <select value={p.goal_type} onChange={(e) => set("goal_type", e.target.value)} className={inputCls}>
          {GOALS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Goal in your words" hint="Only you can see this. It is never added to shared statistics.">
        <textarea
          rows={3}
          value={p.goal_text}
          onChange={(e) => set("goal_text", e.target.value)}
          className={inputCls}
        />
      </Field>
      <ErrorNote message={error} />
      {saved && <SuccessNote>Profile saved.</SuccessNote>}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving" : "Save profile"}
      </Button>
    </form>
  );
}

function DataControls() {
  const [error, setError] = useState<string | null>(null);

  return (
    <section aria-labelledby="data-h" className="mt-14 border-t border-ink pt-4">
      <h2 id="data-h" className="text-xl font-semibold">
        Your data
      </h2>
      <p className="mt-2 text-ink-soft">
        Padhotec stores your profile, courses, study sessions and scores. Deleting your account removes all of it,
        including your entries in the activity log.
      </p>
      <div className="mt-4">
        <ErrorNote message={error} />
        <ConfirmButton
          label="Delete my account and data"
          confirmLabel="Yes, delete everything"
          onConfirm={async () => {
            try {
              await api.deleteAccount();
              tokenStore.clear();
            } catch (e) {
              setError(messageOf(e));
            }
          }}
        />
      </div>
    </section>
  );
}
