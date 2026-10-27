"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { type AuthUser, fetchMe, loginUser, logoutUser, registerUser } from "@/services/authService";

interface AuthValue {
  user: AuthUser | null; loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (payload: { username: string; email: string; password: string; full_name: string }) => Promise<void>;
  logout: () => Promise<void>;
}
const AuthContext = createContext<AuthValue | undefined>(undefined);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const cache = useQueryClient();
  useEffect(() => {
    let alive = true;
    localStorage.removeItem("auth_token"); // Discard credentials left by the earlier version.
    fetchMe().then(u => { if (alive) setUser(u); }).catch(() => { if (alive) setUser(null); })
      .finally(() => { if (alive) setLoading(false); });
    const expire = () => { setUser(null); cache.clear(); };
    window.addEventListener("auth-expired", expire);
    return () => { alive = false; window.removeEventListener("auth-expired", expire); };
  }, [cache]);
  const login = useCallback(async (username: string, password: string) => {
    const result = await loginUser(username, password); cache.clear(); setUser(result.user);
  }, [cache]);
  const register = useCallback(async (payload: {username: string; email: string; password: string; full_name: string}) => {
    const result = await registerUser(payload); cache.clear(); setUser(result.user);
  }, [cache]);
  const logout = useCallback(async () => {
    await logoutUser(); cache.clear(); setUser(null);
  }, [cache]);
  const value = useMemo(() => ({user, loading, login, register, logout}), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider missing"); return value; }
