"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/axios";
import type { Dashboard } from "@/types/domain";
import { StatCard } from "@/components/ui/StatCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ScoreBar } from "@/components/ui/ScoreBar";

export default function DashboardPage() {
  const query = useQuery({queryKey:["dashboard"], queryFn:async () => (await apiClient.get<Dashboard>("/dashboard/")).data,refetchInterval:10000});
  if (query.isPending) return <LoadingSpinner />;
  if (query.isError) return <p role="alert">Unable to load dashboard. Check the API connection.</p>;
  const data = query.data;
  return <div className="space-y-8">
    <section className="rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-700 p-8 text-white">
      <p className="text-sm uppercase tracking-widest">Recruiter workspace</p>
      <h2 className="mt-3 text-3xl font-semibold">Evidence before decisions</h2>
      <p className="mt-3 max-w-2xl">Review resume evidence, compare job-specific criteria, and record your own hiring decisions. Matching scores are advisory.</p>
    </section>
    <div className="grid gap-4 md:grid-cols-4">
      <StatCard label="Candidates" value={data.candidates} helper="Your private candidate pool" />
      <StatCard label="Jobs" value={data.jobs} helper="Your job requirements" />
      <StatCard label="Current matches" value={data.scores.total} helper="Excludes stale results" />
      <StatCard label="Average score" value={`${Math.round(data.scores.average || 0)}%`} helper="Rubric score, not hiring probability" />
    </div>
    <div className="grid gap-6 xl:grid-cols-3">
      <section className="rounded-3xl border bg-white p-6 xl:col-span-2">
        <h3 className="text-lg font-semibold">Audit activity</h3>
        <p className="mt-1 text-sm text-slate-500">Persisted actions; timestamps show when they occurred.</p>
        <div className="mt-5 space-y-3">{data.events.map(event => <div key={event.id} className="rounded-xl bg-slate-50 p-4">
          <p className="font-medium">{event.action.replaceAll(".", " ")}</p>
          <p className="text-sm text-slate-500">{event.target_type} #{event.target_id} · {new Date(event.created_at).toLocaleString()}</p>
        </div>)}{!data.events.length && <p>No activity yet. Create a job and upload a CV.</p>}</div>
      </section>
      <div className="space-y-6">
        <section className="rounded-3xl border bg-white p-6"><h3 className="font-semibold">Match distribution</h3>
          {(["high","medium","low"] as const).map(bucket => <div key={bucket} className="mt-4"><p className="mb-2 capitalize">{bucket}: {data.scores[bucket]} / {data.scores.total}</p>
            <ScoreBar value={data.scores.total ? data.scores[bucket] / data.scores.total * 100 : 0} /></div>)}
        </section>
        <section className="rounded-3xl border bg-white p-6"><h3 className="font-semibold">Processing health</h3>
          <p className="mt-3">{data.worker_online ? "Worker heartbeat received" : "No recent worker heartbeat"}</p>
          <p className="mt-2 text-sm">{data.queued} queued · {data.failed} failed</p>
          <Link href="/automation" className="mt-4 inline-block text-blue-700">Inspect tasks and retry →</Link>
        </section>
      </div>
    </div>
  </div>;
}
