"use client";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { mainNavigation, settingsNavigation, navigationActive } from "./navigation";

export function DashboardLayout({ children }: {children: ReactNode}) {
  const pathname = usePathname();
  return <div className="min-h-screen bg-slate-50 text-slate-900"><a href="#workspace-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:p-3">Skip to content</a><div className="flex min-h-screen">
    <div className="sticky top-0 hidden h-screen lg:block"><Sidebar/></div>
    <main id="workspace-content" className="flex min-h-screen min-w-0 flex-1 flex-col"><Topbar/>
      <nav aria-label="Mobile navigation" className="flex gap-2 overflow-x-auto border-b bg-white px-4 py-3 lg:hidden">{[...mainNavigation, settingsNavigation].map(item => <Link key={item.href} href={item.href} aria-current={navigationActive(pathname, item.href) ? "page" : undefined} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm ${navigationActive(pathname, item.href) ? "bg-blue-600 text-white" : "bg-slate-50 text-slate-600"}`}>{item.label}</Link>)}</nav>
      <div className="flex-1 p-4 sm:p-6 md:p-8">{children}</div>
    </main>
  </div></div>;
}
