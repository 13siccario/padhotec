"use client";

import { useState } from "react";
import { Button, ConfirmButton, ErrorNote, Field, PageHeader, inputCls } from "@/components/ui";
import { api, type Course } from "@/lib/api";
import { messageOf, useLoad } from "@/lib/hooks";
import { parseDate } from "@/lib/stats";

export default function CoursesPage() {
  const { data: courses, error, loading, reload } = useLoad(api.courses);
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
    <div className="max-w-2xl">
      <PageHeader
        title="Courses"
        lead="Add each course you study and break it into topics. Give a topic a higher weight if it counts for more in the exam."
      />
      <ErrorNote message={error ?? actionError} />
      <NewCourseForm onAdd={(name, date) => run(() => api.addCourse(name, date))} />

      {loading && <p className="mt-8 text-ink-soft">Loading courses</p>}
      <div className="mt-10 space-y-10">
        {courses?.map((course) => (
          <CourseSection key={course.id} course={course} run={run} />
        ))}
      </div>
    </div>
  );
}

function NewCourseForm({ onAdd }: { onAdd: (name: string, examDate: string | null) => Promise<void> }) {
  const [name, setName] = useState("");
  const [date, setDate] = useState("");

  return (
    <form
      className="mt-4 flex flex-wrap items-end gap-4"
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
  );
}

function CourseSection({ course, run }: { course: Course; run: (a: () => Promise<unknown>) => Promise<void> }) {
  const [name, setName] = useState("");
  const [weight, setWeight] = useState("1");

  return (
    <section aria-labelledby={`c-${course.id}`} className="border-t border-ink pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={`c-${course.id}`} className="text-xl font-semibold">
          {course.name}
        </h2>
        <div className="flex items-center gap-4 text-sm text-ink-soft">
          {course.exam_date && (
            <span>Exam {parseDate(course.exam_date).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}</span>
          )}
          <ConfirmButton
            label="Delete course"
            confirmLabel="Delete course and its logs"
            onConfirm={() => run(() => api.deleteCourse(course.id))}
          />
        </div>
      </div>

      {course.topics.length === 0 ? (
        <p className="mt-3 text-ink-soft">No topics yet. Add the first one below.</p>
      ) : (
        <ul className="mt-3 divide-y divide-rule border-y border-rule">
          {course.topics.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-4 py-2">
              <span>
                {t.name} <span className="ml-2 text-sm text-ink-soft">weight {t.weight}</span>
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
        className="mt-4 flex flex-wrap items-end gap-4"
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
    </section>
  );
}
