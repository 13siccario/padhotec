"use client";

import Link from "next/link";
import { CourseSection } from "@/components/CourseSection";
import { RiskPanel } from "@/components/RiskPanel";
import { api } from "@/lib/api";
import { useLoad } from "@/lib/hooks";
import { formatMinutes, lastSevenDays, nextExam, parseDate } from "@/lib/stats";

async function loadDashboard() {
  const [courses, sessions, assessments, profile, insights] = await Promise.all([
    api.courses(),
    api.sessions(),
    api.assessments(),
    api.profile(),
    api.insights(),
  ]);
  return { courses, sessions, assessments, profile, insights };
}

export default function DashboardPage() {
  const { data, error, loading } = useLoad(loadDashboard);

  if (loading) return <p className="text-ink-soft">Loading your dashboard</p>;
  if (error || !data) return <p role="alert" className="text-red">{error ?? "Could not load your dashboard."}</p>;

  const { courses, sessions, assessments, profile, insights } = data;
  const now = new Date();

  if (courses.length === 0) {
    return (
      <div className="max-w-lg">
        <h1 className="text-3xl font-semibold tracking-tight">Start with a course</h1>
        <p className="mt-3 text-ink-soft">
          Add a course and its topics, then log what you study. Your dashboard fills in from there.
        </p>
        <Link href="/courses" className="mt-6 inline-block rounded-sm bg-blue px-4 py-2 font-medium text-white hover:bg-blue-deep">
          Add a course
        </Link>
      </div>
    );
  }

  const exam = nextExam(courses, now);
  const week = lastSevenDays(sessions, now);
  const weekMinutes = week.reduce((sum, d) => sum + d.minutes, 0);
  const goalMinutes = profile.weekly_study_hours ? profile.weekly_study_hours * 60 : null;
  const scale = Math.max(60, ...week.map((d) => d.minutes));
  const courseName = new Map(courses.map((c) => [c.id, c.name]));
  const recent = [...assessments]
    .sort((a, b) => parseDate(b.taken_at).getTime() - parseDate(a.taken_at).getTime())
    .slice(0, 5);

  return (
    <div className="space-y-12">
      <header>
        {exam ? (
          <>
            <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
              {exam.course.name} exam {exam.days === 0 ? "is today" : exam.days === 1 ? "is tomorrow" : `in ${exam.days} days`}
            </h1>
            <p className="mt-2 text-ink-soft">
              {parseDate(exam.course.exam_date as string).toLocaleDateString(undefined, {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </p>
          </>
        ) : (
          <>
            <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">Your study overview</h1>
            <p className="mt-2 text-ink-soft">
              Add an exam date to a course and Padhotec will count down to it.{" "}
              <Link href="/courses" className="text-blue underline">
                Set a date
              </Link>
            </p>
          </>
        )}
      </header>

      <section aria-labelledby="week-h">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="week-h" className="text-xl font-semibold">
            This week
          </h2>
          <p className="tabular-nums text-ink-soft">
            {formatMinutes(weekMinutes)}
            {goalMinutes ? ` of ${formatMinutes(goalMinutes)} goal` : ""}
          </p>
        </div>
        <div className="mt-4 flex h-32 items-end gap-2 border-b border-ink tabular-nums">
          {week.map((d, i) => (
            <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <span className="text-xs text-ink-soft">{d.minutes > 0 ? d.minutes : ""}</span>
              <div
                className={`w-full max-w-10 ${d.isToday ? "bg-ink" : "bg-blue"}`}
                style={{ height: `${Math.max((d.minutes / scale) * 100, d.minutes > 0 ? 4 : 0)}%` }}
                role="img"
                aria-label={`${d.label}: ${d.minutes} minutes`}
              />
            </div>
          ))}
        </div>
        <div className="mt-1 flex gap-2">
          {week.map((d, i) => (
            <span key={i} className={`flex-1 text-center text-sm ${d.isToday ? "font-medium text-ink" : "text-ink-soft"}`}>
              {d.label}
            </span>
          ))}
        </div>
        {sessions.length === 0 && (
          <p className="mt-4 text-ink-soft">
            Nothing logged yet.{" "}
            <Link href="/log" className="text-blue underline">
              Log your first session
            </Link>
          </p>
        )}
      </section>

      <RiskPanel risk={insights.risk} />

      {courses.map((course) => (
        <CourseSection
          key={course.id}
          course={course}
          insight={insights.courses.find((c) => c.course_id === course.id)}
          sessions={sessions}
          assessments={assessments}
          now={now}
        />
      ))}

      {recent.length > 0 && (
        <section aria-labelledby="recent-h">
          <h2 id="recent-h" className="text-xl font-semibold">
            Recent scores
          </h2>
          <ul className="mt-3 divide-y divide-rule border-y border-rule">
            {recent.map((a) => (
              <li key={a.id} className="flex items-baseline justify-between gap-4 py-3">
                <span>
                  <span className="font-medium">{a.title}</span>
                  <span className="ml-2 text-ink-soft">{courseName.get(a.course_id)}</span>
                </span>
                <span className="tabular-nums">
                  {a.score}/{a.max_score}
                  <span className="ml-2 text-ink-soft">{Math.round((a.score / a.max_score) * 100)}%</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
