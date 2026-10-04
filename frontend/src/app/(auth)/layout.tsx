"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { RangeBar } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { hydrated, signedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && signedIn) router.replace("/dashboard");
  }, [hydrated, signedIn, router]);

  return (
    <div className="mx-auto grid min-h-screen max-w-5xl items-center gap-12 px-5 py-12 md:grid-cols-[1.1fr_1fr] md:px-8">
      <section>
        <p className="text-xl font-semibold tracking-tight">padhotec</p>
        <h1 className="mt-8 max-w-md text-4xl font-semibold leading-tight tracking-tight md:text-5xl">
          Know what you know, and how sure you can be.
        </h1>
        <p className="mt-5 max-w-md text-lg text-ink-soft">
          Log what you study and how you score. Padhotec tracks where you stand on each topic and tells you what to do
          next.
        </p>
        <div className="mt-10 flex items-center gap-4 text-sm text-ink-soft">
          <RangeBar from={2} to={4} />
          <span>Confidence in Bayes&apos; rule, before and after a session</span>
        </div>
      </section>
      <section>{children}</section>
    </div>
  );
}
