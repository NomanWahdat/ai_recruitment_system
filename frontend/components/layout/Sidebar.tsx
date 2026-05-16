"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Bot, BriefcaseBusiness, LayoutDashboard, Users, Wand2 } from "lucide-react";

const navigation = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Candidates", href: "/candidates", icon: Users },
  { label: "Jobs", href: "/jobs", icon: BriefcaseBusiness },
  { label: "Rankings", href: "/rankings", icon: BarChart3 },
  { label: "AI Tools", href: "/ai-tools", icon: Wand2 },
  { label: "Automation", href: "/automation", icon: Bot },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-72 flex-col border-r border-slate-200 bg-white/90 px-5 py-6 backdrop-blur">
      <div className="mb-8">
        <div className="text-xs font-semibold uppercase tracking-[0.3em] text-blue-600">AI Recruitment</div>
        <div className="mt-2 text-xl font-semibold text-slate-900">Command Center</div>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Automated screening, matching, ranking, and AI workflows in one dashboard.
        </p>
      </div>

      <nav className="space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition ${
                active
                  ? "bg-blue-600 text-white shadow-soft"
                  : "text-slate-600 hover:bg-blue-50 hover:text-blue-700"
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50 p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-900">System Status</div>
        <p className="mt-1 text-sm text-slate-600">Frontend scaffold ready for API integration.</p>
      </div>
    </aside>
  );
}
