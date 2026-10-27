"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { mainNavigation, settingsNavigation, navigationActive } from "./navigation";

export function Sidebar() {
  const pathname = usePathname();
  return <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-white px-5 py-7">
    <Link href="/" className="mb-9 block"><span className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">AI Recruitment</span><span className="mt-2 block text-xl font-semibold text-slate-950">Hiring workspace</span><span className="mt-2 block text-sm leading-6 text-slate-500">Find the right evidence.<br/>Make your own decisions.</span></Link>
    <nav aria-label="Main navigation" className="space-y-2">{mainNavigation.map(item => {
      const Icon = item.icon; const active = navigationActive(pathname, item.href);
      return <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined} className={`flex items-center gap-3 rounded-xl px-4 py-3 font-medium ${active ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-50"}`}><Icon aria-hidden="true" className="h-5 w-5"/>{item.label}</Link>;
    })}</nav>
    <div className="mt-auto space-y-5 pt-8"><Link href={settingsNavigation.href} aria-current={navigationActive(pathname, settingsNavigation.href) ? "page" : undefined} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium ${navigationActive(pathname, settingsNavigation.href) ? "bg-blue-50 text-blue-800" : "text-slate-600 hover:bg-slate-50"}`}><settingsNavigation.icon aria-hidden="true" className="h-5 w-5"/>{settingsNavigation.label}</Link><p className="px-4 text-xs leading-5 text-slate-500">Your resumes are private.<br/>Always check details before deciding.</p></div>
  </aside>;
}
