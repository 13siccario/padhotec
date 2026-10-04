"use client";

import { useState } from "react";
import { Button, Card, ConfirmButton, ErrorNote, Field, PageHeader, inputCls } from "@/components/ui";
import { api, type Course, type Skill } from "@/lib/api";
import { messageOf, useLoad } from "@/lib/hooks";
import { parseDate } from "@/lib/stats";
import { meshClass } from "@/lib/theme";

export default function CoursesPage() {
  const { data: courses, error, loading, reload } = useLoad(api.courses);
  const { data: skills } = useLoad(api.skills);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setActionError(null);
    try {
      await action();
      reload();
    } catch (e) {
      setActionError(messageOf(e));
    }
  }

  return (
    <div className="max-w-6xl">
      <PageHeader
        title="Courses"
        lead="Add each course you study and break it into topics. Give a topic a higher weight if it counts for more in the exam."
      />
      <ErrorNote message={error ?? actionError} />
      <NewCourseForm onAdd={(name, date) => run(() => api.addCourse(name, date))} />

      {loading && <p className="mt-8 text-ink-soft">Loading courses</p>}
      <div className="mt-5 grid items-start gap-5 lg:grid-cols-2">
        {courses?.map((course) => (
          <CourseSection key={course.id} course={course} run={run} skills={skills ?? []} />
        ))}
      </div>
    </div>
  );
}

function NewCourseForm({ onAdd }: { onAdd: (name: string, examDate: string | null) => Promise<void> }) {
  const [name, setName] = useState("");
  const [date, setDate] = useState("");

  return (
    <Card as="div" className="mt-4 mesh mesh-0 lg:max-w-2xl">
      <form
        className="flex flex-wrap items-end gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          // 09:00 local on the exam day, sent as an absolute time.
          await onAdd(name.trim(), date ? new Date(`${date}T09:00:00`).toISOString() : null);
          setName("");
          setDate("");
        }}
      >
        <Field label="Course name">
          <input required value={name} onChange={(e) => setName(e.target.value)} className={`${inputCls} w-64`} />
        </Field>
        <Field label="Exam date (optional)">
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputCls} />
        </Field>
        <Button type="submit">Add course</Button>
      </form>
    </Card>
  );
}

function CourseSection({
  course,
  run,
  skills,
}: {
  course: Course;
  run: (a: () => Promise<unknown>) => Promise<void>;
  skills: Skill[];
}) {
  const [name, setName] = useState("");
  const [weight, setWeight] = useState("1");

  return (
    <Card aria-labelledby={`c-${course.id}`}>
      <div className="flex flex-wrap items-stretch gap-4">
        <div className={`mesh scrim ${meshClass(course.id)} flex min-h-28 min-w-44 flex-1 flex-col justify-end rounded-3xl p-4 text-white sm:flex-none`}>
          <h2 id={`c-${course.id}`} className="font-serif text-3xl font-normal leading-tight tracking-normal">
            {course.name}
          </h2>
          {course.exam_date && (
            <p className="text-sm text-white/90">
              Exam{" "}
              {parseDate(course.exam_date).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
            </p>
          )}
        </div>
        <div className="ml-auto self-end text-sm">
          <ConfirmButton
            label="Delete course"
            confirmLabel="Delete course and its logs"
            onConfirm={() => run(() => api.deleteCourse(course.id))}
          />
        </div>
      </div>

      {course.topics.length === 0 ? (
        <p className="mt-5 text-ink-soft">No topics yet. Add the first one below.</p>
      ) : (
        <ul className="mt-5 space-y-2">
          {course.topics.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-panel px-4 py-3">
              <span className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <span>
                  {t.name} <span className="ml-1 text-sm text-ink-soft">weight {t.weight}</span>
                </span>
                <select
                  aria-label={`Career skill built by ${t.name}`}
                  value={t.skill_key ?? ""}
                  onChange={(e) => run(() => api.tagTopicSkill(t.id, e.target.value || null))}
                  className="max-w-52 rounded-full border border-line bg-white px-3 py-1.5 text-sm text-ink-soft"
                >
                  <option value="">No career skill</option>
                  {skills.map((sk) => (
                    <option key={sk.key} value={sk.key}>
                      Builds: {sk.label}
                    </option>
                  ))}
                </select>
              </span>
              <ConfirmButton
                label="Delete"
                confirmLabel="Delete topic and its logs"
                onConfirm={() => run(() => api.deleteTopic(t.id))}
              />
            </li>
          ))}
        </ul>
      )}

      <form
        className="mt-5 flex flex-wrap items-end gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          await run(() => api.addTopic(course.id, name.trim(), Number(weight)));
          setName("");
          setWeight("1");
        }}
      >
        <Field label="New topic">
          <input required value={name} onChange={(e) => setName(e.target.value)} className={`${inputCls} w-64`} />
        </Field>
        <Field label="Weight">
          <input
            type="number"
            required
            min={0.1}
            step={0.1}
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            className={`${inputCls} w-24`}
          />
        </Field>
        <Button type="submit" variant="quiet">
          Add topic
        </Button>
      </form>
    </Card>
  );
}
