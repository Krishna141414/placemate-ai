"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  /** set when the backend could not be reached at all */
  offline: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<User | null>;
}

const AuthContext = createContext<AuthValue | null>(null);

export const DEMO_ACCOUNTS = {
  student: { email: "student@placemate.demo", password: "Student@123", label: "Student" },
  coordinator: { email: "coordinator@placemate.demo", password: "Coord@123", label: "Coordinator" },
} as const;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const me = (await api<{ user: User | null }>("/api/auth/session")).user;
      setUser(me);
      setOffline(false);
      return me;
    } catch (error) {
      setUser(null);
      setOffline(error instanceof ApiError && error.status === 0);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api<{ user: User | null }>("/api/auth/session")
      .then(({ user: me }) => {
        if (!alive) return;
        setUser(me);
        setOffline(false);
      })
      .catch((error) => {
        if (!alive) return;
        setUser(null);
        setOffline(error instanceof ApiError && error.status === 0);
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const me = await api<User>("/api/auth/login", { method: "POST", body: { email, password } });
    setUser(me);
    setOffline(false);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ user, loading, offline, login, logout, refresh }), [user, loading, offline, login, logout, refresh]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function homeFor(user: User): string {
  return user.role === "coordinator" ? "/analytics" : "/dashboard";
}
