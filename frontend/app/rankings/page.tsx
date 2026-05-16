"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { getJobs, getJobRankings } from "@/services/jobService";
import { getCandidates } from "@/services/candidateService";
import { getAnalyses } from "@/services/analysisService";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { SkillBadge } from "@/components/ui/SkillBadge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function RankingsPage() {
  const searchParams = useSearchParams();
  const [selectedJobId, setSelectedJobId] = useState<number | "">(searchParams.get("job") ? Number(searchParams.get("job")) : "");

  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const candidatesQuery = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: getAnalyses });
  const rankingQuery = useQuery({
    queryKey: ["job-rankings", selectedJobId],
    queryFn: () => getJobRankings(Number(selectedJobId)),
    enabled: Boolean(selectedJobId),
  });

  useEffect(() => {
    if (!selectedJobId && jobsQuery.data?.length) {
      setSelectedJobId(jobsQuery.data[0].id);
    }
  }, [jobsQuery.data, selectedJobId]);

  const jobs = Array.isArray(jobsQuery.data) ? jobsQuery.data : [];
  const candidates = Array.isArray(candidatesQuery.data) ? candidatesQuery.data : [];
  const analyses = Array.isArray(analysesQuery.data) ? analysesQuery.data : [];

  const rows = useMemo(() => {
    return (rankingQuery.data?.top_candidates || [])
      .map((item: any) => {
        const candidate = candidates.find((entry: any) => entry.id === item.candidate_id);
        const analysis = analyses.find((entry: any) => entry.job === selectedJobId && entry.candidate === item.candidate_id);
        return {
          ...item,
          candidate_name: candidate?.full_name || `Candidate #${item.candidate_id}`,
          matched_skills: analysis?.matched_skills || [],
        };
      })
      .sort((left: any, right: any) => Number(right.match_score) - Number(left.match_score));
  }, [analyses, candidates, rankingQuery.data, selectedJobId]);

  if (jobsQuery.isLoading || candidatesQuery.isLoading || analysesQuery.isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">Rankings</h2>
        <p className="mt-2 text-sm text-slate-500">Select a job and inspect the ranked candidate list with matched skills.</p>
      </div>

      <div className="max-w-xl rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <label className="block text-sm font-medium text-slate-700">
          Select job
          <select value={selectedJobId} onChange={(event) => setSelectedJobId(event.target.value ? Number(event.target.value) : "")} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3">
            <option value="">Choose a job</option>
            {jobs.map((job: any) => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="text-lg font-semibold text-slate-950">Top Candidates</div>
        <div className="mt-5 space-y-4">
          {rows.length ? rows.map((row: any) => (
            <div key={row.candidate_id} className="rounded-2xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-sm uppercase tracking-[0.2em] text-slate-400">Rank #{row.ranking_position}</div>
                  <div className="text-lg font-semibold text-slate-900">{row.candidate_name}</div>
                </div>
                <div className="text-right text-sm font-medium text-slate-700">{Number(row.match_score || 0)}%</div>
              </div>
              <div className="mt-3"><ScoreBar value={Number(row.match_score || 0)} /></div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(row.matched_skills || []).length ? row.matched_skills.map((skill: string) => <SkillBadge key={skill} label={skill} />) : <span className="text-sm text-slate-500">No matched skills recorded.</span>}
              </div>
            </div>
          )) : <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">No ranking data available for the selected job.</div>}
        </div>
      </section>
    </div>
  );
}
