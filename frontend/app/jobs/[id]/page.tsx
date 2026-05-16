"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { getJobById, getJobRankings, runMatchingEngine } from "@/services/jobService";
import { getAnalyses } from "@/services/analysisService";
import { getCandidates } from "@/services/candidateService";
import { parseJob } from "@/services/aiService";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { SkillBadge } from "@/components/ui/SkillBadge";
import { useToast } from "@/components/ui/Toast";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [parsedJob, setParsedJob] = useState<any>(null);

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJobById(jobId),
    enabled: Number.isFinite(jobId),
  });
  const rankingQuery = useQuery({
    queryKey: ["job-rankings", jobId],
    queryFn: () => getJobRankings(jobId),
    enabled: Number.isFinite(jobId),
  });
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: getAnalyses });
  const candidatesQuery = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });

  const parseMutation = useMutation({
    mutationFn: () => parseJob(jobQuery.data?.description || ""),
    onSuccess: (data) => {
      setParsedJob(data);
      pushToast({ title: "Job parsed", description: "AI job understanding completed.", type: "success" });
    },
    onError: () => pushToast({ title: "Parse failed", description: "Unable to parse job description.", type: "error" }),
  });

  const runMatchingMutation = useMutation({
    mutationFn: runMatchingEngine,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["job-rankings", jobId] });
      await queryClient.invalidateQueries({ queryKey: ["analyses"] });
      pushToast({ title: "Matching engine executed", description: "Automation reprocessed successfully.", type: "success" });
    },
    onError: () => pushToast({ title: "Matching failed", description: "Unable to execute matching engine.", type: "error" }),
  });

  const job = jobQuery.data;
  const rankings = rankingQuery.data?.top_candidates || [];
  const analyses = analysesQuery.data || [];
  const candidates = candidatesQuery.data || [];

  const enrichedRankings = useMemo(() => {
    return rankings.map((entry: any) => {
      const analysis = analyses.find((item: any) => item.job === jobId && item.candidate === entry.candidate_id);
      const candidate = candidates.find((item: any) => item.id === entry.candidate_id);
      return {
        ...entry,
        candidate_name: candidate?.full_name || `Candidate #${entry.candidate_id}`,
        matched_skills: analysis?.matched_skills || [],
      };
    });
  }, [analyses, candidates, jobId, rankings]);

  if (jobQuery.isLoading) return <LoadingSpinner />;
  if (jobQuery.isError || !job) {
    return <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 shadow-soft">Job not found.</div>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">Job detail</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-950">{job.title}</h2>
          <p className="mt-2 text-sm text-slate-500">{job.company_name} • {job.location || "Location not specified"}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => parseMutation.mutate()} className="rounded-2xl bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-soft ring-1 ring-slate-200">Parse Job</button>
          <button onClick={() => runMatchingMutation.mutate()} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-soft">Run Matching Engine</button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft xl:col-span-2">
          <div className="text-lg font-semibold text-slate-950">Job Description</div>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-600">{job.description || "No description available."}</p>
          <div className="mt-6">
            <div className="mb-2 text-sm font-medium text-slate-700">Required skills</div>
            <div className="flex flex-wrap gap-2">
              {(job.required_skills || []).length ? job.required_skills.map((skill: string) => <SkillBadge key={skill} label={skill} />) : <span className="text-sm text-slate-500">No required skills listed.</span>}
            </div>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <div className="font-medium text-slate-900">Minimum experience</div>
              <p className="mt-1">{job.minimum_experience ?? 0} years</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
              <div className="font-medium text-slate-900">Education requirement</div>
              <p className="mt-1">{job.education_requirement || "Not specified"}</p>
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">AI Parsed Insights</div>
            <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-600">{parsedJob ? JSON.stringify(parsedJob, null, 2) : "Run parsing to see structured insights."}</pre>
          </section>
        </aside>
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
        <div className="text-lg font-semibold text-slate-950">Ranked Candidates</div>
        <div className="mt-5 space-y-4">
          {enrichedRankings.length ? enrichedRankings.map((entry: any) => (
            <div key={entry.candidate_id} className="rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-medium text-slate-900">{entry.candidate_name}</div>
                  <div className="text-sm text-slate-500">Rank #{entry.ranking_position || "-"}</div>
                </div>
                <div className="text-right text-sm font-medium text-slate-700">{Number(entry.match_score || 0)}%</div>
              </div>
              <div className="mt-3"><ScoreBar value={Number(entry.match_score || 0)} /></div>
              <div className="mt-3 flex flex-wrap gap-2">{(entry.matched_skills || []).map((skill: string) => <SkillBadge key={skill} label={skill} />)}</div>
            </div>
          )) : <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">No rankings available yet.</div>}
        </div>
      </section>
    </div>
  );
}
