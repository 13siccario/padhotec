"use client";

import Link from "next/link";
import { Card, ErrorNote, IntervalBar, PageHeader, SectionTitle } from "@/components/ui";
import { api, type PeerMetric } from "@/lib/api";
import { useLoad } from "@/lib/hooks";

export default function PeersPage() {
  const { data, error, loading } = useLoad(api.peers);

  return (
    <div className="max-w-6xl">
      <PageHeader
        title="Peers"
        lead="See how your study habits compare with similar students. Nobody is named, and a group is only shown when at least 5 other students are in it."
      />
      <ErrorNote message={error} />
      {loading && <p className="text-ink-soft">Loading</p>}

      {data?.status === "opted_out" && (
        <p className="max-w-prose text-ink-soft">
          {data.note}{" "}
          <Link href="/profile" className="font-medium text-ink underline">
            Go to your profile
          </Link>
        </p>
      )}

      {data?.status === "ok" && (
        <div className="grid items-start gap-5 lg:grid-cols-[1.4fr_1fr]">
          <Card aria-labelledby="group-h" className="mesh mesh-soft lg:col-span-2">
            <SectionTitle id="group-h">Compared with</SectionTitle>
            <p className="mt-2">
              {data.label}
              {data.cohort_size !== null && (
                <span className="text-ink-soft">, {data.cohort_size} students</span>
              )}
            </p>
            {data.note && <p className="mt-2 max-w-prose text-ink-soft">{data.note}</p>}
          </Card>

          <Card aria-labelledby="habits-h">
            <SectionTitle id="habits-h">Study habits</SectionTitle>
            <ul className="mt-4 divide-y divide-line">
              {data.metrics.map((m) => (
                <MetricRow key={m.key} m={m} />
              ))}
            </ul>
            <p className="mt-3 max-w-prose text-sm text-ink-soft">
              The bar shows the middle half of the group. The dot is the group&apos;s median and the diamond is you. More
              is not always better: this is context, not a target. Group figures are rounded.
            </p>
          </Card>

          {data.common_topics.length > 0 && (
            <Card aria-labelledby="topics-h">
              <SectionTitle id="topics-h" count={data.common_topics.length} tone="bg-sticky">
                Topics others track
              </SectionTitle>
              <ul className="mt-4 space-y-2">
                {data.common_topics.map((t) => (
                  <li key={`${t.course}-${t.topic}`} className="rounded-2xl bg-sticky px-4 py-3">
                    <span className="font-medium">{t.topic}</span>
                    <span className="ml-2 text-ink-soft">
                      {t.peers_tracking} of {t.cohort_size} students on {t.course} track this and you don&apos;t.
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-4">
                <Link href="/courses" className="font-medium text-ink underline">
                  Add a topic
                </Link>
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function MetricRow({ m }: { m: PeerMetric }) {
  const scale = Math.max(m.p75 * 1.4, (m.you ?? 0) * 1.2, 1);
  const unit = m.unit;
  return (
    <li className="grid gap-x-6 gap-y-3 py-4 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="font-medium">{m.label}</p>
        <p className="text-ink-soft">
          {m.you !== null ? `You: ${m.you} ${unit}. ` : ""}
          {m.p25 === m.p75
            ? `Most of the group: about ${m.p25} ${unit}.`
            : `Middle half of the group: ${m.p25} to ${m.p75} ${unit}.`}
        </p>
        {m.position ? (
          <p>You are in the {m.position}.</p>
        ) : (
          <p className="text-ink-soft">Log a few weeks of study to see where you sit.</p>
        )}
      </div>
      <IntervalBar
        mean={m.median / scale}
        lo={m.p25 / scale}
        hi={m.p75 / scale}
        marker={m.you === null ? null : m.you / scale}
        width="w-44"
        label={`${m.label}. Group median ${m.median} ${unit}, middle half ${m.p25} to ${m.p75}.${
          m.you !== null ? ` You: ${m.you}.` : ""
        }`}
      />
    </li>
  );
}
