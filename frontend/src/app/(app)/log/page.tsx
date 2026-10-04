"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, ErrorNote, Field, PageHeader, SuccessNote, inputCls } from "@/components/ui";
import { api, type Assessment, type Course } from "@/lib/api";
import { messageOf, useLoad } from "@/lib/hooks";

export default function LogPage() {
  const { data: courses, error, loading } = useLoad(api.courses);
  const [tab, setTab] = useState<"session" | "score">("session");

  return (
    <div className="max-w-xl">
      <PageHeader title="Log" lead="Takes under a minute. Regular small entries tell Padhotec more than rare long ones." />

      <div role="tablist" aria-label="What to log" className="mb-6 inline-flex rounded-sm border border-ink">
        {(
          [
            ["session", "Study session"],
            ["score", "Score"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-base ${tab === id ? "bg-ink font-medium text-white" : "bg-white text-ink hover:bg-paper"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <ErrorNote message={error} />
      {loading && <p className="text-ink-soft">Loading</p>}
      {courses && courses.every((c) => c.topics.length === 0) ? (
        <p className="text-ink-soft">
          You need at least one course with a topic before you can log.{" "}
          <Link href="/courses" className="text-blue underline">
            Add courses and topics
          </Link>
        </p>
      ) : (
        courses && (tab === "session" ? <SessionForm courses={courses} /> : <ScoreForm courses={courses} />)
      )}
    </div>
  );
}

function RatingInput({ label, value, onChange }: { label: string; value: number | null; onChange: (v: number | null) => void }) {
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-medium">{label}</legend>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            type="button"
            key={n}
            aria-pressed={value === n}
            onClick={() => onChange(value === n ? null : n)}
            className={`size-10 rounded-sm border text-base ${
              value === n ? "border-blue bg-blue font-medium text-white" : "border-rule bg-white hover:border-ink"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <p className="mt-1 text-sm text-ink-soft">1 is lost, 5 is confident. Optional.</p>
    </fieldset>
  );
}

function SessionForm({ courses }: { courses: Course[] }) {
  const topics = courses.flatMap((c) => c.topics);
  const [topicId, setTopicId] = useState<number>(topics[0]?.id ?? 0);
  const [minutes, setMinutes] = useState("");
  const [before, setBefore] = useState<number | null>(null);
  const [after, setAfter] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(null);
    setBusy(true);
    try {
      const saved = await api.logSession({
        topic_id: topicId,
        minutes: Number(minutes),
        confidence_before: before,
        confidence_after: after,
      });
      const name = topics.find((t) => t.id === topicId)?.name;
      setDone(`Logged ${saved.minutes} min on ${name}.`);
      setMinutes("");
      setBefore(null);
      setAfter(null);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <Field label="Topic">
        <select value={topicId} onChange={(e) => setTopicId(Number(e.target.value))} className={inputCls}>
          {courses
            .filter((c) => c.topics.length > 0)
            .map((c) => (
              <optgroup key={c.id} label={c.name}>
                {c.topics.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </optgroup>
            ))}
        </select>
      </Field>
      <Field label="Minutes studied">
        <input
          type="number"
          required
          min={1}
          max={720}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          className={`${inputCls} w-32`}
        />
        <span className="mt-2 flex gap-2">
          {[15, 30, 45, 60].map((m) => (
            <button
              type="button"
              key={m}
              onClick={() => setMinutes(String(m))}
              className="rounded-sm border border-rule bg-white px-3 py-1 text-sm hover:border-ink"
            >
              {m}
            </button>
          ))}
        </span>
      </Field>
      <RatingInput label="Confidence before" value={before} onChange={setBefore} />
      <RatingInput label="Confidence after" value={after} onChange={setAfter} />
      <ErrorNote message={error} />
      {done && <SuccessNote>{done}</SuccessNote>}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving" : "Log session"}
      </Button>
    </form>
  );
}

function ScoreForm({ courses }: { courses: Course[] }) {
  const [courseId, setCourseId] = useState<number>(courses[0]?.id ?? 0);
  const [topicId, setTopicId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<Assessment["kind"]>("quiz");
  const [score, setScore] = useState("");
  const [max, setMax] = useState("100");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const course = courses.find((c) => c.id === courseId);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(null);
    if (Number(score) > Number(max)) {
      setError("Score can't be higher than the maximum.");
      return;
    }
    setBusy(true);
    try {
      const saved = await api.recordAssessment({
        course_id: courseId,
        topic_id: topicId,
        title: title.trim(),
        kind,
        score: Number(score),
        max_score: Number(max),
      });
      setDone(`Saved ${saved.title}: ${saved.score}/${saved.max_score}.`);
      setTitle("");
      setScore("");
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <Field label="Course">
        <select
          value={courseId}
          onChange={(e) => {
            setCourseId(Number(e.target.value));
            setTopicId(null);
          }}
          className={inputCls}
        >
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Topic" hint="Pick one if the score covers a single topic.">
        <select
          value={topicId ?? ""}
          onChange={(e) => setTopicId(e.target.value ? Number(e.target.value) : null)}
          className={inputCls}
        >
          <option value="">Whole course</option>
          {course?.topics.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Title">
          <input required value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />
        </Field>
        <Field label="Type">
          <select value={kind} onChange={(e) => setKind(e.target.value as Assessment["kind"])} className={inputCls}>
            <option value="quiz">Quiz</option>
            <option value="assignment">Assignment</option>
            <option value="mock">Mock exam</option>
            <option value="exam">Exam</option>
          </select>
        </Field>
      </div>
      <div className="flex items-end gap-3">
        <Field label="Score">
          <input
            type="number"
            required
            min={0}
            step="any"
            value={score}
            onChange={(e) => setScore(e.target.value)}
            className={`${inputCls} w-28`}
          />
        </Field>
        <span className="pb-2 text-ink-soft">out of</span>
        <Field label="Maximum">
          <input
            type="number"
            required
            min={0.01}
            step="any"
            value={max}
            onChange={(e) => setMax(e.target.value)}
            className={`${inputCls} w-28`}
          />
        </Field>
      </div>
      <ErrorNote message={error} />
      {done && <SuccessNote>{done}</SuccessNote>}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving" : "Save score"}
      </Button>
    </form>
  );
}
