"use client";

import { BookOpen, Compass, LayoutGrid, LogOut, PenLine, ShieldCheck, UserRound, Users } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { LogoMark } from "@/components/Logo";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLoad } from "@/lib/hooks";

const NAV = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutGrid },
  { href: "/log", label: "Log", Icon: PenLine, accent: true },
  { href: "/courses", label: "Courses", Icon: BookOpen },
  { href: "/career", label: "Career", Icon: Compass },
  { href: "/peers", label: "Peers", Icon: Users },
  { href: "/profile", label: "Profile", Icon: UserRound },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const { hydrated, signedIn, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (hydrated && !signedIn) router.replace("/login");
  }, [hydrated, signedIn, router]);

  if (!hydrated || !signedIn) return null;

  return (
    <div className="min-h-screen md:p-5">
      <div className="mx-auto flex min-h-screen max-w-[1320px] gap-4 bg-canvas md:min-h-[calc(100vh-2.5rem)] md:rounded-[40px] md:p-4 md:ring-1 md:ring-white/70">
        <aside className="sticky top-5 hidden h-[calc(100vh-3.5rem)] w-[92px] shrink-0 flex-col items-center justify-between self-start rounded-[28px] bg-white py-5 ring-1 ring-black/[0.04] md:flex">
          <div className="flex flex-col items-center gap-5">
            <Link href="/dashboard" aria-label="Padhotec home">
              <LogoMark size={40} />
            </Link>
            <nav aria-label="Main" className="flex flex-col items-center gap-1.5">
              {NAV.map((item) => (
                <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} />
              ))}
            </nav>
          </div>
          <div className="flex flex-col items-center gap-1">
            <Link
              href="/evaluation"
              className="flex w-[68px] flex-col items-center gap-0.5 rounded-2xl py-2.5 text-ink-soft transition-colors hover:bg-panel hover:text-ink"
            >
              <ShieldCheck size={22} strokeWidth={1.75} aria-hidden="true" />
              <span className="text-xs leading-none">Evidence</span>
            </Link>
            <button
              onClick={logout}
              aria-label="Sign out"
              title="Sign out"
              className="flex size-11 items-center justify-center rounded-2xl text-ink-soft transition-colors hover:bg-panel hover:text-ink"
            >
              <LogOut size={20} strokeWidth={1.75} aria-hidden="true" />
            </button>
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-4 pb-32 pt-6 md:px-4 md:pb-8 md:pt-4">
          <DemoBanner />
          {children}
        </main>
      </div>

      <nav
        aria-label="Main"
        className="fixed inset-x-3 bottom-3 z-10 flex justify-around rounded-full bg-white/95 px-2 py-1.5 shadow-[0_8px_30px_rgba(60,40,20,0.14)] ring-1 ring-black/5 backdrop-blur md:hidden"
      >
        {NAV.map((item) => (
          <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} compact />
        ))}
      </nav>
    </div>
  );
}

function NavLink({
  href,
  label,
  Icon,
  active,
  accent,
  compact,
}: {
  href: string;
  label: string;
  Icon: typeof LayoutGrid;
  active: boolean;
  accent?: boolean;
  compact?: boolean;
}) {
  const tone = accent ? "bg-yellow text-ink" : active ? "bg-panel text-ink" : "text-ink-soft hover:bg-panel hover:text-ink";
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`flex flex-col items-center justify-center gap-0.5 rounded-2xl transition-colors ${tone} ${
        compact ? "min-w-[3.25rem] px-1.5 py-1.5" : "w-[68px] py-2.5"
      } ${accent && active ? "ring-2 ring-ink" : ""}`}
    >
      <Icon size={compact ? 20 : 22} strokeWidth={active ? 2.25 : 1.75} aria-hidden="true" />
      <span className={`leading-none ${compact ? "text-[11px]" : "text-xs"} ${active ? "font-semibold" : ""}`}>
        {label}
      </span>
    </Link>
  );
}

/** Shown only on demo accounts, so synthetic data is never mistaken for real results. */
function DemoBanner() {
  const { data } = useLoad(api.me);
  if (!data?.is_demo) return null;
  return (
    <p role="note" className="mb-5 rounded-2xl bg-sticky px-4 py-3 text-sm text-ink">
      <strong>Demo account.</strong> Everything here is invented to show how Padhotec works, so none of it is evidence. The
      real test results are on the{" "}
      <Link href="/evaluation" className="font-medium underline">
        evidence page
      </Link>
      .
    </p>
  );
}
