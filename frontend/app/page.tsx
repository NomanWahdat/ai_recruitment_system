"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getCandidates } from "@/services/candidateService";
import { getJobs } from "@/services/jobService";
import { getAnalyses } from "@/services/analysisService";
import { StatCard } from "@/components/ui/StatCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ScoreBar } from "@/components/ui/ScoreBar";

function toNumber(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export default function DashboardPage() {
  const candidatesQuery = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });
  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: getAnalyses });

  const candidates = Array.isArray(candidatesQuery.data) ? candidatesQuery.data : [];
  const jobs = Array.isArray(jobsQuery.data) ? jobsQuery.data : [];
  const analyses = Array.isArray(analysesQuery.data) ? analysesQuery.data : [];

  const dashboard = useMemo(() => {
    const totalMatches = analyses.length;
    const averageMatchScore = analyses.length
      ? Math.round(analyses.reduce((sum: number, analysis: any) => sum + toNumber(analysis.match_score), 0) / analyses.length)
      : 0;

    const recentActivity = [
      ...candidates.slice(0, 3).map((candidate: any) => ({
        type: "Candidate upload",
        title: candidate.full_name,
        subtitle: candidate.email,
        date: candidate.uploaded_at,
        href: `/candidates/${candidate.id}`,
      })),
      ...jobs.slice(0, 3).map((job: any) => ({
        type: "Job posted",
        title: job.title,
        subtitle: job.company_name,
        date: job.created_at,
        href: `/jobs/${job.id}`,
      })),
      ...analyses.slice(0, 3).map((analysis: any) => ({
        type: "AI analysis",
        title: `Match ${analysis.match_score}%`,
        subtitle: `Candidate #${analysis.candidate} ↔ Job #${analysis.job}`,
        date: analysis.analysis_created_at,
        href: `/rankings?job=${analysis.job}`,
      })),
    ]
      .filter((item) => item.date)
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      .slice(0, 8);

    const buckets = {
      high: analyses.filter((analysis: any) => toNumber(analysis.match_score) > 80).length,
      medium: analyses.filter((analysis: any) => toNumber(analysis.match_score) >= 50 && toNumber(analysis.match_score) <= 80).length,
      low: analyses.filter((analysis: any) => toNumber(analysis.match_score) < 50).length,
    };

    return { totalMatches, averageMatchScore, recentActivity, buckets };
  }, [analyses, candidates, jobs]);

  if (candidatesQuery.isLoading || jobsQuery.isLoading || analysesQuery.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-44 w-full rounded-3xl" />
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <Skeleton className="h-28 rounded-3xl" />
          <Skeleton className="h-28 rounded-3xl" />
          <Skeleton className="h-28 rounded-3xl" />
          <Skeleton className="h-28 rounded-3xl" />
        </div>
      </div>
    );
  }

  if (candidatesQuery.isError || jobsQuery.isError || analysesQuery.isError) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 shadow-soft">
        <div className="text-lg font-semibold text-slate-900">Unable to load dashboard data</div>
        <p className="mt-2 text-sm text-slate-500">Check the backend API connection and try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-600 to-indigo-700 p-8 text-white shadow-soft">
        <div className="max-w-3xl space-y-4">
          <div className="text-sm font-medium uppercase tracking-[0.25em] text-blue-100">Dashboard</div>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">AI Recruitment Control Center</h2>
          <p className="max-w-2xl text-sm leading-7 text-blue-50 md:text-base">
            Monitor candidates, jobs, AI insights, and automation workflows from one professional SaaS dashboard.
          </p>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Candidates" value={candidates.length} helper="Uploaded profiles" />
        <StatCard label="Total Jobs" value={jobs.length} helper="Open positions" />
        <StatCard label="Total Matches" value={dashboard.totalMatches} helper="Stored analyses" />
        <StatCard label="Average Match Score" value={`${dashboard.averageMatchScore}%`} helper="Across all analyses" />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft xl:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-slate-950">Recent Activity</div>
              <p className="mt-1 text-sm text-slate-500">Latest uploads, jobs, and AI analysis events.</p>
            </div>
            <Link href="/automation" className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
              View Automation
            </Link>
          </div>

          <div className="mt-5 space-y-3">
            {dashboard.recentActivity.length ? dashboard.recentActivity.map((item) => (
              <Link key={`${item.type}-${item.title}-${item.date}`} href={item.href} className="block rounded-2xl border border-slate-200 p-4 transition hover:border-blue-200 hover:bg-blue-50/40">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                    <div className="text-sm text-slate-500">{item.subtitle}</div>
                  </div>
                  <div className="text-xs font-medium uppercase tracking-[0.2em] text-blue-600">{item.type}</div>
                </div>
                <div className="mt-2 text-xs text-slate-400">{new Date(item.date).toLocaleString()}</div>
              </Link>
            )) : <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">No activity yet.</div>}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Match Distribution</div>
            <div className="mt-4 space-y-4 text-sm text-slate-600">
              <div>
                <div className="mb-2 flex items-center justify-between"><span>High (&gt;80)</span><span>{dashboard.buckets.high}</span></div>
                <ScoreBar value={Math.min(100, dashboard.buckets.high * 20)} />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between"><span>Medium (50-80)</span><span>{dashboard.buckets.medium}</span></div>
                <ScoreBar value={Math.min(100, dashboard.buckets.medium * 20)} />
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between"><span>Low (&lt;50)</span><span>{dashboard.buckets.low}</span></div>
                <ScoreBar value={Math.min(100, dashboard.buckets.low * 20)} />
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Quick Links</div>
            <div className="mt-4 grid gap-3">
              <Link href="/candidates" className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">Manage Candidates</Link>
              <Link href="/jobs" className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">Manage Jobs</Link>
              <Link href="/ai-tools" className="rounded-2xl bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">Open AI Tools</Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
