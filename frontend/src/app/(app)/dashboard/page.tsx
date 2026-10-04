"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { CourseSection } from "@/components/CourseSection";
import { PlanPanel } from "@/components/PlanPanel";
import { RiskPanel } from "@/components/RiskPanel";
import { Card, Panel, ProgressBar, SectionTitle, btnPrimary } from "@/components/ui";
import { api, type Assessment, type Course } from "@/lib/api";
import { useLoad } from "@/lib/hooks";
import { formatMinutes, lastSevenDays, nextExam, parseDate, pct } from "@/lib/stats";
import { meshClass, scoreTone } from "@/lib/theme";

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

function greeting(now: Date): string {
  const h = now.getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const { data, error, loading } = useLoad(loadDashboard);

  if (loading) return <p className="p-4 text-ink-soft">Loading your dashboard</p>;
  if (error || !data) return <p role="alert" className="p-4 text-bad">{error ?? "Could not load your dashboard."}</p>;

  const { courses, sessions, assessments, profile, insights } = data;
  const now = new Date();
  const first = profile.display_name.trim().split(/\s+/)[0];
  const hello = `${greeting(now)}${first ? `, ${first}` : ""},`;

  if (courses.length === 0) {
    return (
      <div className="space-y-6">
        <Hero hello={hello} line="let's get you set up." />
        <Card className="mesh mesh-0 max-w-xl">
          <h2 className="text-3xl font-normal">Start with a course</h2>
          <p className="mt-2 max-w-md text-ink">
            Add a course and its topics, then log what you study. Your dashboard fills in from there.
          </p>
          <Link href="/courses" className={`${btnPrimary} mt-6`}>
            Add a course
          </Link>
        </Card>
      </div>
    );
  }

  const exam = nextExam(courses, now);
  const when = exam
    ? exam.days === 0
      ? "is today"
      : exam.days === 1
        ? "is tomorrow"
        : `in ${exam.days} days`
    : "";
  const week = lastSevenDays(sessions, now);
  const weekMinutes = week.reduce((sum, d) => sum + d.minutes, 0);
  const goalMinutes = profile.weekly_study_hours ? profile.weekly_study_hours * 60 : null;
  const scale = Math.max(60, ...week.map((d) => d.minutes));
  const courseName = new Map(courses.map((c) => [c.id, c.name]));
  const recent = [...assessments]
    .sort((a, b) => parseDate(b.taken_at).getTime() - parseDate(a.taken_at).getTime())
    .slice(0, 4);

  return (
    <div className="space-y-5">
      <Hero
        hello={hello}
        line={exam ? `${exam.course.name} exam ${when}.` : "here's your study overview."}
        date={
          exam
            ? parseDate(exam.course.exam_date as string).toLocaleDateString(undefined, {
                weekday: "long",
                day: "numeric",
                month: "long",
              })
            : undefined
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        <PlanPanel />
        <RiskPanel risk={insights.risk} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        <Card aria-labelledby="week-h">
          <SectionTitle id="week-h">This week</SectionTitle>
          <p className="mt-4 text-ink-soft">
            <span className="font-display text-4xl font-normal tabular-nums text-ink">{formatMinutes(weekMinutes)}</span>
            {goalMinutes ? ` of ${formatMinutes(goalMinutes)} goal` : ""}
          </p>
          {goalMinutes && (
            <div className="mt-3 max-w-xs">
              <ProgressBar fraction={weekMinutes / goalMinutes} />
            </div>
          )}
          <div className="mt-6 flex h-36 items-end gap-2.5 tabular-nums">
            {week.map((d, i) => (
              <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
                <span className="text-xs text-ink-soft">{d.minutes > 0 ? d.minutes : ""}</span>
                <div
                  className={`w-full max-w-12 rounded-2xl ${d.isToday ? "bg-ink" : "bg-yellow"} ${
                    d.minutes === 0 ? "bg-black/[0.06]" : ""
                  }`}
                  style={{ height: `${Math.max((d.minutes / scale) * 100, d.minutes > 0 ? 6 : 4)}%` }}
                  role="img"
                  aria-label={`${d.label}: ${d.minutes} minutes`}
                />
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-2.5">
            {week.map((d, i) => (
              <span key={i} className={`flex-1 text-center text-sm ${d.isToday ? "font-semibold text-ink" : "text-ink-soft"}`}>
                {d.label}
              </span>
            ))}
          </div>
          {sessions.length === 0 && (
            <p className="mt-4 text-ink-soft">
              Nothing logged yet.{" "}
              <Link href="/log" className="font-medium text-ink underline">
                Log your first session
              </Link>
            </p>
          )}
        </Card>

        <RecentScores items={recent} courseName={courseName} />
      </div>

      <Panel aria-labelledby="courses-h">
        <div className="mb-4 flex items-center justify-between gap-3 px-1">
          <SectionTitle id="courses-h" count={courses.length} tone="bg-white">
            Your courses
          </SectionTitle>
        </div>
        <CourseTiles courses={courses} />
      </Panel>

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
    </div>
  );
}

function Hero({ hello, line, date }: { hello: string; line: string; date?: string }) {
  return (
    <header className="max-w-3xl pb-2 pt-1">
      <h1 className="text-4xl font-normal leading-[1.08] md:text-6xl">
        {hello}
        <span className="block text-ink-mute">{line}</span>
      </h1>
      {date && <p className="mt-3 text-ink-soft">{date}</p>}
    </header>
  );
}

function CourseTiles({ courses }: { courses: Course[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {courses.map((c) => (
        <a
          key={c.id}
          href={`#course-${c.id}`}
          className={`mesh scrim ${meshClass(c.id)} flex aspect-[1/1.02] flex-col justify-end rounded-3xl p-4 text-white transition-transform hover:-translate-y-0.5`}
        >
          <span className="font-serif text-2xl leading-tight">{c.name}</span>
          <span className="text-sm text-white/90">
            {c.topics.length} topic{c.topics.length === 1 ? "" : "s"}
          </span>
        </a>
      ))}
      <Link
        href="/courses"
        className="col-span-2 flex items-center justify-between gap-4 rounded-3xl bg-gradient-to-r from-[#f3e7a4] via-[#f1dbe8] to-[#f6eef0] px-5 py-4 md:col-span-4"
      >
        <span className="text-lg font-medium">Add a course</span>
        <span className="flex size-11 items-center justify-center rounded-2xl bg-white">
          <Plus size={22} aria-hidden="true" />
        </span>
      </Link>
    </div>
  );
}

function RecentScores({ items, courseName }: { items: Assessment[]; courseName: Map<number, string> }) {
  return (
    <Card aria-labelledby="recent-h">
      <SectionTitle id="recent-h" count={items.length || undefined} tone="bg-peach">
        Recent scores
      </SectionTitle>
      {items.length === 0 ? (
        <p className="mt-4 text-ink-soft">
          No scores yet.{" "}
          <Link href="/log" className="font-medium text-ink underline">
            Log a score
          </Link>
        </p>
      ) : (
        <ul className="mt-5 space-y-3">
          {items.map((a) => {
            const f = a.score / a.max_score;
            const tone = scoreTone(f);
            return (
              <li key={a.id} className="rounded-2xl bg-panel p-4">
                <div className="flex items-baseline justify-between gap-3">
                  <span>
                    <span className="font-medium">{a.title}</span>
                    <span className="ml-2 text-sm text-ink-soft">{courseName.get(a.course_id)}</span>
                  </span>
                  <span className="tabular-nums">
                    {a.score}/{a.max_score}
                  </span>
                </div>
                <div className="mt-2.5 flex items-center gap-3">
                  <ProgressBar fraction={f} barClass={tone.bar} />
                  <span className={`w-10 shrink-0 text-right text-sm font-medium tabular-nums ${tone.text}`}>
                    {pct(f)}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
