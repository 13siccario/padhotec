"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogoMark, Wordmark } from "@/components/Logo";
import { IntervalBar } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { hydrated, signedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && signedIn) router.replace("/dashboard");
  }, [hydrated, signedIn, router]);

  return (
    <div className="mesh-soft min-h-screen px-5 py-10 md:px-10">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-12 md:grid-cols-[1.15fr_1fr]">
        <section>
          <div className="flex items-center gap-3">
            <LogoMark size={44} />
            <Wordmark className="text-5xl md:text-7xl" />
          </div>
          <h1 className="mt-10 max-w-2xl text-3xl font-normal leading-[1.1] sm:text-4xl md:text-5xl lg:text-6xl">
            Know what you know,
            <span className="block text-ink-mute">and how sure you can be.</span>
          </h1>
          <p className="mt-5 max-w-md text-lg text-ink-soft">
            Log what you study and how you score. Padhotec tracks where you stand on each topic and tells you what to do
            next.
          </p>
          <Link href="/evaluation" className="mt-4 inline-block font-medium underline">
            See how accurate it is
          </Link>

          {/* A taste of the product. Decorative: the real numbers live on the dashboard. */}
          <div aria-hidden="true" className="relative mt-12 hidden h-56 max-w-md md:block">
            <div className="absolute left-0 top-6 w-64 -rotate-3 rounded-[24px] bg-white/85 p-4 shadow-[0_10px_40px_rgba(60,40,20,0.12)] ring-1 ring-white backdrop-blur">
              <p className="text-sm text-ink-soft">Bayes&apos; rule</p>
              <p className="mt-1 text-4xl font-semibold">65%</p>
              <p className="mb-3 text-sm text-ink-soft">likely between 45% and 83%</p>
              <IntervalBar mean={0.65} lo={0.45} hi={0.83} label="" width="w-full" />
            </div>
            <div className="absolute left-48 top-0 w-44 rotate-6 rounded-[22px] bg-sticky p-4 shadow-[0_10px_40px_rgba(60,40,20,0.1)]">
              <p className="text-sm text-ink-soft">Next up</p>
              <p className="mt-1 text-lg leading-snug">Test yourself on Regression for 10 minutes</p>
            </div>
          </div>
        </section>
        <section>{children}</section>
      </div>
    </div>
  );
}
