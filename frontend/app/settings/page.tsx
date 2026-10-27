"use client";
import Link from "next/link";
import { BarChart3, BookOpen, Bot, ListOrdered, Wand2 } from "lucide-react";
const tools = [
  {title: "Processing activity", href: "/automation", description: "See resume progress, retry a failed upload, or refresh your matching results.", icon: Bot},
  {title: "AI assistant tools", href: "/ai-tools", description: "Use the standalone job, explanation and interview tools. Check your AI connection here.", icon: Wand2},
  {title: "Compare across jobs", href: "/rankings", description: "Switch between jobs to view their current candidate rankings.", icon: ListOrdered},
  {title: "System testing", href: "/evaluation", description: "Technical benchmark results, known limitations, and downloadable evaluation data.", icon: BarChart3},
];
export default function SettingsPage() {
  return <div className="space-y-7"><div><h2 className="text-2xl font-semibold">Settings & tools</h2><p className="mt-2 max-w-2xl text-slate-600">Everything beyond day-to-day hiring is here. You can also use matching, explanations and interview questions directly from a candidate.</p></div>
    <section className="rounded-2xl border border-blue-100 bg-blue-50 p-6"><h3 className="font-semibold text-blue-950">Looking for your next hiring step?</h3><p className="mt-2 text-sm text-blue-900">Open a job to add resumes and compare candidates. Check a candidate&apos;s details before recording a decision.</p><Link href="/jobs" className="mt-4 inline-block rounded-xl bg-blue-600 px-4 py-2 text-sm text-white">Open jobs</Link></section>
    <div className="grid gap-5 md:grid-cols-2">{tools.map(tool => <Link key={tool.href} href={tool.href} className="rounded-2xl border bg-white p-6 transition hover:border-blue-300"><tool.icon aria-hidden="true" className="h-6 w-6 text-blue-600"/><h3 className="mt-4 font-semibold">{tool.title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{tool.description}</p><span className="mt-4 inline-block text-sm font-medium text-blue-700">Open tool</span></Link>)}</div>
    <section className="rounded-2xl border bg-white p-6"><BookOpen aria-hidden="true" className="h-5 w-5 text-slate-500"/><h3 className="mt-3 font-semibold">What the scores mean</h3><p className="mt-2 text-sm leading-6 text-slate-600">Scores compare the resume details with the requirements you set. They support your review; they do not predict whether someone will succeed in a job. Open the calculation details on a candidate to see the breakdown, verify a saved score, download its technical data or inspect previous comparisons.</p></section>
  </div>;
}
