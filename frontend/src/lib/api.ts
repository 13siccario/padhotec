const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "padhotec.token";

// Token store, observable so React can subscribe with useSyncExternalStore.
// localStorage keeps this simple for v1; move to httpOnly cookies before a public launch.
const listeners = new Set<() => void>();

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {}
    listeners.forEach((l) => l());
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {}
    listeners.forEach((l) => l());
  },
  subscribe(listener: () => void) {
    listeners.add(listener);
    window.addEventListener("storage", listener);
    return () => {
      listeners.delete(listener);
      window.removeEventListener("storage", listener);
    };
  },
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

function detailToMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
    return field ? `${String(field)}: ${first.msg ?? "invalid value"}` : (first.msg ?? "Invalid input");
  }
  return "Something went wrong";
}

async function request<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.json !== undefined) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
      body: init.json !== undefined ? JSON.stringify(init.json) : init.body,
    });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // An expired or invalid token on a protected call signs the user out.
    if (res.status === 401 && token) tokenStore.clear();
    const retry = res.headers.get("Retry-After");
    const message =
      res.status === 429 && retry
        ? `Too many attempts. Try again in ${Math.ceil(Number(retry) / 60)} min.`
        : detailToMessage(body?.detail);
    throw new ApiError(message, res.status);
  }
  return body as T;
}

export type Topic = { id: number; course_id: number; name: string; weight: number };
export type Course = { id: number; name: string; exam_date: string | null; topics: Topic[] };
export type StudySession = {
  id: number;
  topic_id: number;
  minutes: number;
  confidence_before: number | null;
  confidence_after: number | null;
  started_at: string;
};
export type Assessment = {
  id: number;
  course_id: number;
  topic_id: number | null;
  title: string;
  kind: "quiz" | "assignment" | "exam" | "mock";
  score: number;
  max_score: number;
  taken_at: string;
};
export type Profile = {
  display_name: string;
  institution: string;
  degree: string;
  year: number | null;
  goal_type: string;
  goal_text: string;
  weekly_study_hours: number | null;
};

export type Mastery = {
  mean: number;
  lo: number;
  hi: number;
  evidence: number;
  n_observations: number;
  last_evidence_at: string | null;
};
export type Performance = {
  mean: number;
  lo: number;
  hi: number;
  p_pass: number;
  pass_mark: number;
  covered_weight: number;
};
export type CourseInsight = {
  course_id: number;
  name: string;
  exam_date: string | null;
  topics: { topic_id: number; name: string; weight: number; mastery: Mastery }[];
  performance: Performance | null;
  performance_note: string | null;
};
export type Risk = {
  status: "ok" | "insufficient_data";
  message: string | null;
  probability: number | null;
  typical: number | null;
  level: "low" | "elevated" | "high" | null;
  horizon_days: number;
  drivers: { label: string; effect: "raises" | "lowers"; detail: string }[];
  model_version: string | null;
};
export type Insights = { generated_at: string; courses: CourseInsight[]; risk: Risk };

export const api = {
  register: (email: string, password: string, consent: boolean) =>
    request<{ access_token: string }>("/auth/register", { method: "POST", json: { email, password, consent } }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", { method: "POST", json: { email, password } }),
  me: () => request<{ id: number; email: string }>("/auth/me"),
  deleteAccount: () => request<void>("/auth/me", { method: "DELETE" }),

  profile: () => request<Profile>("/profile"),
  saveProfile: (p: Profile) => request<Profile>("/profile", { method: "PUT", json: p }),

  courses: () => request<Course[]>("/courses"),
  addCourse: (name: string, exam_date: string | null) =>
    request<Course>("/courses", { method: "POST", json: { name, exam_date } }),
  deleteCourse: (id: number) => request<void>(`/courses/${id}`, { method: "DELETE" }),
  addTopic: (courseId: number, name: string, weight: number) =>
    request<Topic>(`/courses/${courseId}/topics`, { method: "POST", json: { name, weight } }),
  deleteTopic: (id: number) => request<void>(`/courses/topics/${id}`, { method: "DELETE" }),

  insights: () => request<Insights>("/insights"),

  sessions: () => request<StudySession[]>("/sessions"),
  logSession: (s: Pick<StudySession, "topic_id" | "minutes" | "confidence_before" | "confidence_after">) =>
    request<StudySession>("/sessions", {
      method: "POST",
      json: Object.fromEntries(Object.entries(s).filter(([, v]) => v !== null)),
    }),
  assessments: () => request<Assessment[]>("/assessments"),
  recordAssessment: (a: {
    course_id: number;
    topic_id: number | null;
    title: string;
    kind: Assessment["kind"];
    score: number;
    max_score: number;
  }) =>
    request<Assessment>("/assessments", {
      method: "POST",
      json: Object.fromEntries(Object.entries(a).filter(([, v]) => v !== null)),
    }),
};
