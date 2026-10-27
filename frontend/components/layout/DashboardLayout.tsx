"use client";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import type { ReactNode } from "react";
import Link from "next/link";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/60 text-slate-900">
      <div className="flex min-h-screen">
        <div className="sticky top-0 hidden h-screen lg:block">
          <Sidebar />
        </div>

        <main className="flex min-h-screen min-w-0 flex-1 flex-col">
          <Topbar />
          <nav aria-label="Mobile navigation" className="flex flex-wrap gap-3 border-b bg-white p-4 lg:hidden">{["candidates","jobs","rankings","evaluation","ai-tools","automation"].map(path=><Link key={path} href={`/${path}`} className="rounded-lg border px-3 py-2 capitalize">{path.replace("-"," ")}</Link>)}<Link href="/" className="rounded-lg border px-3 py-2">Dashboard</Link></nav>
          <div className="flex-1 p-6 md:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
