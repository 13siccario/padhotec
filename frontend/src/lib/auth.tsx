"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";
import { api, tokenStore } from "@/lib/api";

type AuthState = {
  /** False until the browser has been read, so pages don't flash the wrong screen. */
  hydrated: boolean;
  signedIn: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, consent: boolean) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

const noop = () => () => {};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const token = useSyncExternalStore(tokenStore.subscribe, tokenStore.get, () => null);
  const hydrated = useSyncExternalStore(noop, () => true, () => false);

  const login = useCallback(async (email: string, password: string) => {
    tokenStore.set((await api.login(email, password)).access_token);
  }, []);
  const register = useCallback(async (email: string, password: string, consent: boolean) => {
    tokenStore.set((await api.register(email, password, consent)).access_token);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ hydrated, signedIn: token !== null, login, register, logout: tokenStore.clear }),
    [hydrated, token, login, register],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
