"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, ErrorNote, Field, inputCls } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { messageOf } from "@/lib/hooks";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isRegister) await register(email, password, consent);
      else await login(email, password);
      // The auth layout redirects once the token is stored.
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5 rounded-[28px] bg-white p-7 shadow-[0_10px_40px_rgba(60,40,20,0.08)] ring-1 ring-black/[0.04]">
      <h2 className="text-3xl font-normal">{isRegister ? "Create your account" : "Sign in"}</h2>
      <Field label="Email">
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputCls}
        />
      </Field>
      <Field label="Password" hint={isRegister ? "At least 8 characters." : undefined}>
        <input
          type="password"
          required
          minLength={isRegister ? 8 : undefined}
          autoComplete={isRegister ? "new-password" : "current-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={inputCls}
        />
      </Field>
      {isRegister && (
        <label className="flex gap-3 text-sm text-ink-soft">
          <input
            type="checkbox"
            required
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1 size-4 accent-black"
          />
          <span>
            I agree that Padhotec stores my study logs and scores to calculate my progress. Anything shared with other
            students is combined into groups of at least 5, and I can delete all my data at any time.
          </span>
        </label>
      )}
      <ErrorNote message={error} />
      <Button type="submit" disabled={busy} className="w-full">
        {busy ? "Please wait" : isRegister ? "Create account" : "Sign in"}
      </Button>
      <p className="text-sm text-ink-soft">
        {isRegister ? "Already have an account? " : "New to Padhotec? "}
        <Link href={isRegister ? "/login" : "/register"} className="font-medium text-ink underline">
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
