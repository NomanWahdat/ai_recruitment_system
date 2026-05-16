"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Bell, LogOut, Search, Settings, User, UserCircle2 } from "lucide-react";
import { getCandidates } from "@/services/candidateService";
import { getJobs } from "@/services/jobService";
import { useAuth } from "@/contexts/AuthContext";

/* ── Search result type ─────────────────────────────── */
interface SearchHit {
  label: string;
  subtitle: string;
  href: string;
  type: "candidate" | "job";
}

export function Topbar() {
  const router = useRouter();
  const { user, logout } = useAuth();

  /* ── Global search state ───────────────────────────── */
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const { data: candidates } = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });
  const { data: jobs } = useQuery({ queryKey: ["jobs"], queryFn: getJobs });

  const hits: SearchHit[] = (() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    const results: SearchHit[] = [];

    for (const c of (candidates as any[]) || []) {
      const text = `${c.full_name} ${c.email} ${(c.skills || []).join(" ")}`.toLowerCase();
      if (text.includes(q)) {
        results.push({ label: c.full_name, subtitle: c.email, href: `/candidates/${c.id}`, type: "candidate" });
      }
    }
    for (const j of (jobs as any[]) || []) {
      const text = `${j.title} ${j.company_name} ${j.description || ""}`.toLowerCase();
      if (text.includes(q)) {
        results.push({ label: j.title, subtitle: j.company_name, href: `/jobs/${j.id}`, type: "job" });
      }
    }
    return results.slice(0, 8);
  })();

  const showResults = focused && query.trim().length > 0;

  const handleSelect = useCallback((href: string) => {
    setQuery("");
    setFocused(false);
    router.push(href);
  }, [router]);

  // Close dropdown on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setFocused(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  /* ── Profile dropdown state ────────────────────────── */
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  /* ── Notification state ─────────────────────────────── */
  const [notifOpen, setNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  const totalCandidates = Array.isArray(candidates) ? candidates.length : 0;
  const totalJobs = Array.isArray(jobs) ? jobs.length : 0;
  const notifications = [
    ...(totalCandidates > 0 ? [{ text: `${totalCandidates} candidate${totalCandidates > 1 ? "s" : ""} in the system`, time: "Just now" }] : []),
    ...(totalJobs > 0 ? [{ text: `${totalJobs} active job${totalJobs > 1 ? "s" : ""} posted`, time: "Just now" }] : []),
    { text: "AI matching engine is online", time: "System" },
  ];

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-4 backdrop-blur">
      <div>
        <div className="text-sm font-medium text-slate-500">Recruitment Dashboard</div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950">AI Operations Workspace</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* ── Global search ─────────────────────────────── */}
        <div ref={searchRef} className="relative">
          <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-500 shadow-sm">
            <Search className="h-4 w-4" />
            <input
              aria-label="Global search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setFocused(true)}
              placeholder="Search candidates, jobs..."
              className="w-56 border-0 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
            />
          </label>

          {showResults && (
            <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              {hits.length ? (
                <ul className="max-h-72 overflow-auto py-1">
                  {hits.map((hit) => (
                    <li key={hit.href}>
                      <button
                        onClick={() => handleSelect(hit.href)}
                        className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-blue-50"
                      >
                        <span className={`mt-0.5 rounded-lg px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${hit.type === "candidate" ? "bg-emerald-100 text-emerald-700" : "bg-violet-100 text-violet-700"}`}>
                          {hit.type === "candidate" ? "C" : "J"}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium text-slate-900">{hit.label}</div>
                          <div className="truncate text-xs text-slate-500">{hit.subtitle}</div>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="px-4 py-6 text-center text-sm text-slate-500">No results for &ldquo;{query}&rdquo;</div>
              )}
            </div>
          )}
        </div>

        {/* ── Notifications ─────────────────────────────── */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => { setNotifOpen(!notifOpen); setProfileOpen(false); }}
            className="relative inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:text-blue-700"
          >
            <Bell className="h-4 w-4" />
            {notifications.length > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[9px] font-bold text-white">
                {notifications.length}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-72 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              <div className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-900">Notifications</div>
              <ul className="max-h-60 overflow-auto">
                {notifications.map((n, i) => (
                  <li key={i} className="border-b border-slate-50 px-4 py-3 last:border-0">
                    <div className="text-sm text-slate-700">{n.text}</div>
                    <div className="mt-0.5 text-xs text-slate-400">{n.time}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* ── Profile dropdown ──────────────────────────── */}
        <div ref={profileRef} className="relative">
          <button
            onClick={() => { setProfileOpen(!profileOpen); setNotifOpen(false); }}
            className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:text-blue-700"
          >
            <UserCircle2 className="h-5 w-5" />
          </button>

          {profileOpen && (
            <div className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
              <div className="border-b border-slate-100 px-4 py-3">
                <div className="text-sm font-semibold text-slate-900">{user?.full_name || "User"}</div>
                <div className="text-xs text-slate-500">{user?.email || user?.username}</div>
              </div>
              <nav className="py-1">
                <Link
                  href="/"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 transition hover:bg-slate-50"
                >
                  <User className="h-4 w-4 text-slate-400" />
                  Dashboard
                </Link>
                <Link
                  href="/automation"
                  onClick={() => setProfileOpen(false)}
                  className="flex items-center gap-3 px-4 py-2.5 text-sm text-slate-700 transition hover:bg-slate-50"
                >
                  <Settings className="h-4 w-4 text-slate-400" />
                  Automation Settings
                </Link>
                <button
                  onClick={async () => { setProfileOpen(false); await logout(); }}
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-rose-600 transition hover:bg-rose-50"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </button>
              </nav>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
