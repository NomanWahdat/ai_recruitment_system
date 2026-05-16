"use client";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import type { ReactNode } from "react";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/60 text-slate-900">
      <div className="flex min-h-screen">
        <div className="sticky top-0 hidden h-screen lg:block">
          <Sidebar />
        </div>

        <main className="flex min-h-screen flex-1 flex-col">
          <Topbar />
          <div className="flex-1 p-6 md:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
