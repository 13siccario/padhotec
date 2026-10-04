"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/log", label: "Log" },
  { href: "/courses", label: "Courses" },
  { href: "/profile", label: "Profile" },
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
    <div className="mx-auto flex min-h-screen max-w-6xl">
      <aside className="sticky top-0 hidden h-screen w-52 shrink-0 flex-col justify-between border-r border-rule bg-paper/90 px-6 py-8 md:flex">
        <div>
          <Link href="/dashboard" className="text-xl font-semibold tracking-tight text-ink">
            padhotec
          </Link>
          <nav aria-label="Main" className="mt-10 flex flex-col gap-1">
            {NAV.map((item) => (
              <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} />
            ))}
          </nav>
        </div>
        <button onClick={logout} className="text-left text-sm text-ink-soft underline hover:text-ink">
          Sign out
        </button>
      </aside>

      <main className="min-w-0 flex-1 px-5 pb-28 pt-8 md:px-12 md:pb-12 md:pt-12">{children}</main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-10 flex justify-around border-t border-rule bg-paper px-2 py-1 md:hidden"
      >
        {NAV.map((item) => (
          <NavLink key={item.href} {...item} active={pathname.startsWith(item.href)} />
        ))}
      </nav>
    </div>
  );
}

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`rounded-sm px-3 py-2 text-base ${
        active ? "bg-ink font-medium text-white" : "text-ink-soft hover:bg-white hover:text-ink"
      }`}
    >
      {label}
    </Link>
  );
}
