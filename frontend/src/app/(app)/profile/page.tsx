"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, ConfirmButton, ErrorNote, Field, PageHeader, SuccessNote, inputCls } from "@/components/ui";
import { useAuth } from "@/lib/auth";
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
    <div className="max-w-6xl">
      <PageHeader title="Profile" lead="Your goal and weekly hours shape the plans Padhotec builds for you." />
      <ErrorNote message={error} />
      {loading && <p className="text-ink-soft">Loading</p>}
      <div className="grid items-start gap-5 lg:grid-cols-2">
        {data && <ProfileForm initial={data} />}
        <div className="space-y-5">
          <PrivacyControl />
          <EvidenceLink />
          <AccountControls />
          <DataControls />
        </div>
      </div>
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
    <form onSubmit={submit} className="space-y-5 rounded-[28px] bg-white p-6 ring-1 ring-black/[0.04] md:p-7">
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

function PrivacyControl() {
  const { data, error, loading } = useLoad(api.privacy);

  return (
    <section aria-labelledby="privacy-h" className="rounded-[28px] bg-white p-6 ring-1 ring-black/[0.04] md:p-7">
      <h2 id="privacy-h" className="text-2xl font-normal">
        Peer statistics
      </h2>
      <p className="mt-2 max-w-prose text-ink-soft">
        Other students can see combined figures about study time and topics, only in groups of at least 5 and with
        rounded numbers. Nobody is named. If you turn this off, you are left out of everyone&apos;s figures and you
        don&apos;t see peer statistics either.
      </p>
      <div className="mt-4">
        <ErrorNote message={error} />
        {loading && <p className="text-ink-soft">Loading</p>}
        {data && <PeerOptIn initialOptOut={data.peer_stats_opt_out} />}
      </div>
    </section>
  );
}

/** Responds instantly, saves in the background, and goes back with a message if the save fails. */
function PeerOptIn({ initialOptOut }: { initialOptOut: boolean }) {
  const [included, setIncluded] = useState(!initialOptOut);
  const [error, setError] = useState<string | null>(null);

  async function change(next: boolean) {
    setError(null);
    setIncluded(next);
    try {
      await api.setPrivacy(!next);
    } catch (e) {
      setIncluded(!next);
      setError(`Couldn't save that change. ${messageOf(e)}`);
    }
  }

  return (
    <div className="space-y-3">
      <ErrorNote message={error} />
      <label className="flex items-center gap-3">
        <input
          type="checkbox"
          checked={included}
          onChange={(e) => change(e.target.checked)}
          className="size-4 accent-black"
        />
        Include me in peer statistics
      </label>
    </div>
  );
}

function EvidenceLink() {
  return (
    <section aria-labelledby="evidence-h" className="rounded-[28px] bg-white p-6 ring-1 ring-black/[0.04] md:p-7">
      <h2 id="evidence-h" className="text-2xl font-normal">
        About the numbers
      </h2>
      <p className="mt-2 max-w-prose text-ink-soft">
        How the models were tested, how often they are right, and what they cannot tell you.
      </p>
      <Link href="/evaluation" className="mt-4 inline-flex rounded-full border border-ink px-5 py-2.5 font-medium hover:bg-white">
        See the evidence
      </Link>
    </section>
  );
}

function AccountControls() {
  const { logout } = useAuth();
  return (
    <section aria-labelledby="account-h" className="rounded-[28px] bg-white p-6 ring-1 ring-black/[0.04] md:p-7">
      <h2 id="account-h" className="text-2xl font-normal">
        Session
      </h2>
      <p className="mt-2 max-w-prose text-ink-soft">Sign out on this device. Your data stays saved.</p>
      <div className="mt-4">
        <Button variant="quiet" onClick={logout}>
          Sign out
        </Button>
      </div>
    </section>
  );
}

function DataControls() {
  const [error, setError] = useState<string | null>(null);

  return (
    <section aria-labelledby="data-h" className="rounded-[28px] bg-white p-6 ring-1 ring-black/[0.04] md:p-7">
      <h2 id="data-h" className="text-2xl font-normal">
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
