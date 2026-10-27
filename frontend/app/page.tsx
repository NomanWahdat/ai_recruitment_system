"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/axios";
import type { Dashboard } from "@/types/domain";
import { StatCard } from "@/components/ui/StatCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { HiringSteps } from "@/components/ui/HiringSteps";

export default function DashboardPage() {
  const query = useQuery({queryKey: ["dashboard"], queryFn: async () => (await apiClient.get<Dashboard>("/dashboard/")).data, refetchInterval: 10000});
  if (query.isPending) return <LoadingSpinner/>;
  if (query.isError) return <p role="alert">We couldn&apos;t load your workspace. Please try again.</p>;
  const data = query.data;
  return <div className="space-y-6">
    <section className="rounded-3xl bg-blue-700 p-6 text-white sm:p-8"><p className="text-sm text-blue-100">Your hiring workspace</p><h2 className="mt-2 text-3xl font-semibold">Let&apos;s find your next candidate</h2><p className="mt-3 max-w-2xl leading-7 text-blue-50">Start with a job, add resumes, and check the details. We help you compare; you make the decision.</p><div className="mt-6 flex flex-wrap gap-3"><Link href="/jobs?new=1" className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-blue-800">Create a job</Link><Link href="/candidates?upload=1" className="rounded-xl border border-blue-300 px-5 py-3 text-sm font-medium">Upload resumes</Link></div></section>
    <HiringSteps/>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><StatCard label="Your jobs" value={data.jobs} helper="Roles you are recruiting for"/><StatCard label="Candidates" value={data.candidates} helper="Your private candidate pool"/><StatCard label="Current comparisons" value={data.scores.total} helper="Based on the latest saved details"/><StatCard label="Resumes in progress" value={data.queued} helper="You can keep working while we process them"/></div>
    <section className="rounded-2xl border bg-white p-6"><h3 className="text-lg font-semibold">What would you like to do?</h3><div className="mt-5 grid gap-4 md:grid-cols-3">{[
      ["/jobs", "Continue hiring", "Open a job to compare candidates and review its requirements."],
      ["/candidates", "Check candidate details", "Review extracted information against the original resume."],
      ["/automation", data.failed ? `${data.failed} processing issues need attention` : "Check resume progress", data.failed ? "See which files need a clearer copy or another attempt." : "View reading progress and completed uploads."],
    ].map(([href,title,description]) => <Link key={href} href={href} className="rounded-xl border p-5 hover:border-blue-300"><h4 className="font-semibold text-blue-800">{title}</h4><p className="mt-2 text-sm leading-6 text-slate-600">{description}</p></Link>)}</div>{!data.worker_online && data.queued > 0 && <p role="status" className="mt-4 text-sm text-amber-800">Resume processing is temporarily unavailable. Your uploads are saved; check processing activity for updates.</p>}</section>
    <details className="rounded-2xl border bg-white p-6"><summary className="cursor-pointer font-semibold">Recent activity and comparison overview</summary><div className="mt-5 grid gap-6 xl:grid-cols-2"><div className="space-y-3">{data.events.map(event => <div key={event.id} className="rounded-xl bg-slate-50 p-4"><p className="text-sm font-medium">{event.action.replaceAll(".", " ").replaceAll("_", " ")}</p><p className="mt-1 text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</p><details className="mt-2 text-xs text-slate-500"><summary>Activity details</summary>{event.target_type} #{event.target_id}</details></div>)}{!data.events.length && <p className="text-sm">Your activity will appear here after you create a job or upload a resume.</p>}</div><div><p className="text-sm text-slate-600">Average comparison score: {Math.round(data.scores.average || 0)} / 100. Scores support your review.</p>{(["high", "medium", "low"] as const).map(bucket => <div key={bucket} className="mt-4"><p className="mb-2 text-sm capitalize">{bucket}: {data.scores[bucket]}</p><ScoreBar value={data.scores.total ? data.scores[bucket] / data.scores.total * 100 : 0}/></div>)}<Link href="/settings" className="mt-5 inline-block text-sm text-blue-700">System tools and testing</Link></div></div></details>
  </div>;
}
