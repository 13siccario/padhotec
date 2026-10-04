"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { hydrated, signedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (hydrated) router.replace(signedIn ? "/dashboard" : "/login");
  }, [hydrated, signedIn, router]);

  return null;
}
