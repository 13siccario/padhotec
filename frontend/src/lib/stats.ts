import type { Assessment, Course, StudySession, Topic } from "@/lib/api";

const DAY_MS = 24 * 60 * 60 * 1000;

/** The server stores UTC; SQLite returns it without a zone marker, so treat bare timestamps as UTC. */
export function parseDate(iso: string): Date {
  return new Date(/(Z|[+-]\d\d:?\d\d)$/.test(iso) ? iso : `${iso}Z`);
}

function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

export function daysUntil(iso: string, now: Date): number {
  const target = parseDate(iso);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTarget = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  return Math.round((startOfTarget.getTime() - startOfToday.getTime()) / DAY_MS);
}

export function nextExam(courses: Course[], now: Date): { course: Course; days: number } | null {
  const upcoming = courses
    .filter((c) => c.exam_date)
    .map((course) => ({ course, days: daysUntil(course.exam_date as string, now) }))
    .filter((x) => x.days >= 0)
    .sort((a, b) => a.days - b.days);
  return upcoming[0] ?? null;
}

export type DayTotal = { label: string; minutes: number; isToday: boolean };

/** Minutes studied for each of the last 7 local days, oldest first. */
export function lastSevenDays(sessions: StudySession[], now: Date): DayTotal[] {
  const totals = new Map<string, number>();
  for (const s of sessions) {
    const key = dayKey(parseDate(s.started_at));
    totals.set(key, (totals.get(key) ?? 0) + s.minutes);
  }
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (6 - i));
    return {
      label: d.toLocaleDateString(undefined, { weekday: "short" }),
      minutes: totals.get(dayKey(d)) ?? 0,
      isToday: i === 6,
    };
  });
}

export type TopicSummary = {
  topic: Topic;
  minutes14d: number;
  /** Fraction (0-1) of the most recent score tied to this topic. */
  lastScore: number | null;
};

export function summariseTopics(
  course: Course,
  sessions: StudySession[],
  assessments: Assessment[],
  now: Date,
): TopicSummary[] {
  const since = now.getTime() - 14 * DAY_MS;
  return course.topics.map((topic) => {
    const lastAssessment = assessments
      .filter((a) => a.topic_id === topic.id)
      .sort((a, b) => parseDate(b.taken_at).getTime() - parseDate(a.taken_at).getTime())[0];
    return {
      topic,
      minutes14d: sessions
        .filter((s) => s.topic_id === topic.id && parseDate(s.started_at).getTime() >= since)
        .reduce((sum, s) => sum + s.minutes, 0),
      lastScore: lastAssessment ? lastAssessment.score / lastAssessment.max_score : null,
    };
  });
}

export const pct = (x: number): string => `${Math.round(x * 100)}%`;

/** One decimal below 10%, where whole numbers would hide real differences (2.7% vs 3%). */
export const pct1 = (x: number): string => (x < 0.1 ? `${(x * 100).toFixed(1)}%` : pct(x));

export function formatMinutes(m: number): string {
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return rest === 0 ? `${h} h` : `${h} h ${rest} min`;
}
