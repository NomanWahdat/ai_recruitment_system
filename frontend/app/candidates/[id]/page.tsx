"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { analyzeCandidate, getCandidateById, runMatch } from "@/services/candidateService";
import { getJobs } from "@/services/jobService";
import { getAnalyses } from "@/services/analysisService";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { SkillBadge } from "@/components/ui/SkillBadge";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";

function formatDate(value?: string | null) {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

export default function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const candidateId = Number(params.id);
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [jobId, setJobId] = useState<number | "">("");
  const [showMatchModal, setShowMatchModal] = useState(false);

  const candidateQuery = useQuery({
    queryKey: ["candidate", candidateId],
    queryFn: () => getCandidateById(candidateId),
    enabled: Number.isFinite(candidateId),
  });
  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: getJobs });
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: getAnalyses });

  const runAnalysisMutation = useMutation({
    mutationFn: () => analyzeCandidate(candidateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidate", candidateId] });
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
      pushToast({ title: "Analysis complete", description: "Candidate profile has been refreshed.", type: "success" });
    },
    onError: (error: unknown) => {
      pushToast({ title: "Analysis failed", description: error instanceof Error ? error.message : "Unable to analyze candidate.", type: "error" });
    },
  });

  const runMatchMutation = useMutation({
    mutationFn: () => runMatch(candidateId, Number(jobId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
      queryClient.invalidateQueries({ queryKey: ["candidate", candidateId] });
      pushToast({ title: "Match generated", description: "The selected job has been matched successfully.", type: "success" });
      setShowMatchModal(false);
    },
    onError: (error: unknown) => {
      pushToast({ title: "Matching failed", description: error instanceof Error ? error.message : "Unable to run matching.", type: "error" });
    },
  });

  const candidate = candidateQuery.data;
  const analyses = analysesQuery.data || [];
  const jobs = jobsQuery.data || [];

  const matchHistory = useMemo(() => {
    return analyses
      .filter((analysis: any) => analysis.candidate === candidateId)
      .map((analysis: any) => ({
        ...analysis,
        jobTitle: jobs.find((job: any) => job.id === analysis.job)?.title || `Job #${analysis.job}`,
      }));
  }, [analyses, candidateId, jobs]);

  if (candidateQuery.isLoading) return <LoadingSpinner />;
  if (candidateQuery.isError || !candidate) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 shadow-soft">
        <div className="text-lg font-semibold text-slate-900">Candidate not found</div>
        <p className="mt-2 text-sm text-slate-500">The requested candidate could not be loaded.</p>
        <Link href="/candidates" className="mt-4 inline-flex rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
          Back to candidates
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">Candidate profile</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-950">{candidate.full_name}</h2>
          <p className="mt-2 text-sm text-slate-500">{candidate.email}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => runAnalysisMutation.mutate()} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-soft">
            Run Analysis
          </button>
          <button onClick={() => setShowMatchModal(true)} className="rounded-2xl bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-soft ring-1 ring-slate-200">
            Run Matching
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Extracted Profile</div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div><div className="text-xs uppercase tracking-[0.2em] text-slate-400">Phone</div><div className="mt-1 text-sm text-slate-700">{candidate.phone_number || "N/A"}</div></div>
              <div><div className="text-xs uppercase tracking-[0.2em] text-slate-400">Experience</div><div className="mt-1 text-sm text-slate-700">{candidate.years_of_experience ?? 0} years</div></div>
              <div><div className="text-xs uppercase tracking-[0.2em] text-slate-400">Education</div><div className="mt-1 text-sm text-slate-700">{candidate.education || "N/A"}</div></div>
              <div><div className="text-xs uppercase tracking-[0.2em] text-slate-400">Status</div><div className="mt-1 text-sm text-slate-700">{candidate.analysis_completed ? "Analyzed" : "Not analyzed"}</div></div>
            </div>
            <div className="mt-6">
              <div className="mb-2 text-sm font-medium text-slate-700">Skills</div>
              <div className="flex flex-wrap gap-2">
                {(candidate.skills || []).length ? candidate.skills.map((skill: string) => <SkillBadge key={skill} label={skill} />) : <span className="text-sm text-slate-500">No extracted skills yet.</span>}
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">AI Analysis Result</div>
            <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
              {candidate.analysis_error ? candidate.analysis_error : candidate.analysis_completed ? "Analysis completed successfully." : "Analysis not yet run."}
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-sm font-medium text-slate-700">Extraction status</div>
                <p className="mt-1 text-sm text-slate-500">{candidate.extraction_success ? "CV text extracted" : candidate.extraction_error || "Awaiting extraction"}</p>
              </div>
              <div>
                <div className="text-sm font-medium text-slate-700">Timestamps</div>
                <p className="mt-1 text-sm text-slate-500">Uploaded: {formatDate(candidate.uploaded_at)}</p>
                <p className="text-sm text-slate-500">Analyzed: {formatDate(candidate.analyzed_at)}</p>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Match History</div>
            <div className="mt-5 space-y-4">
              {matchHistory.length ? matchHistory.map((analysis: any) => (
                <div key={analysis.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-medium text-slate-900">{analysis.jobTitle}</div>
                      <div className="text-sm text-slate-500">Position #{analysis.ranking_position ?? "-"}</div>
                    </div>
                    <div className="text-right text-sm font-medium text-slate-700">{analysis.match_score}%</div>
                  </div>
                  <div className="mt-3"><ScoreBar value={Number(analysis.match_score || 0)} /></div>
                  <div className="mt-3 flex flex-wrap gap-2">{(analysis.matched_skills || []).map((skill: string) => <SkillBadge key={skill} label={skill} />)}</div>
                </div>
              )) : <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">No match history yet.</div>}
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Quick Stats</div>
            <div className="mt-4 space-y-3 text-sm text-slate-600">
              <div className="flex items-center justify-between"><span>Processing status</span><span className="font-medium text-slate-900">{candidate.processing_status}</span></div>
              <div className="flex items-center justify-between"><span>Analysis status</span><span className="font-medium text-slate-900">{candidate.analysis_completed ? "Done" : "Pending"}</span></div>
              <div className="flex items-center justify-between"><span>Experience</span><span className="font-medium text-slate-900">{candidate.years_of_experience ?? 0} yrs</span></div>
            </div>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Raw CV Excerpt</div>
            <p className="mt-4 max-h-80 overflow-auto rounded-2xl bg-slate-50 p-4 text-sm leading-7 text-slate-600">
              {candidate.extracted_text || "No extracted text available."}
            </p>
          </section>
        </aside>
      </div>

      <Modal open={showMatchModal} title="Run Matching" onClose={() => setShowMatchModal(false)}>
        <div className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">
            Select Job
            <select value={jobId} onChange={(event) => setJobId(event.target.value ? Number(event.target.value) : "")} className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <option value="">Choose a job</option>
              {jobs.map((job: any) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
          </label>
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowMatchModal(false)} className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">Cancel</button>
            <button disabled={!jobId || runMatchMutation.isPending} onClick={() => runMatchMutation.mutate()} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {runMatchMutation.isPending ? "Running..." : "Run Matching"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
