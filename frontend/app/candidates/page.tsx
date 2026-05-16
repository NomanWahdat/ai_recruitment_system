"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { analyzeCandidate, createCandidate, deleteCandidate, getCandidates } from "@/services/candidateService";
import { getAnalyses } from "@/services/analysisService";
import { CandidateCard } from "@/components/ui/CandidateCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";

const PAGE_SIZE = 6;

function matchesSearch(candidate: any, query: string) {
  const text = `${candidate.full_name || ""} ${candidate.email || ""} ${(candidate.skills || []).join(" ")}`.toLowerCase();
  return text.includes(query.toLowerCase());
}

export default function CandidatesPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [search, setSearch] = useState("");
  const [analysisFilter, setAnalysisFilter] = useState<"all" | "analyzed" | "not_analyzed">("all");
  const [experienceFilter, setExperienceFilter] = useState<"all" | "0-2" | "3-5" | "6+">("all");
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [formState, setFormState] = useState({ full_name: "", email: "", phone_number: "" });
  const [cvFile, setCvFile] = useState<File | null>(null);

  const candidatesQuery = useQuery({ queryKey: ["candidates"], queryFn: getCandidates });
  const analysesQuery = useQuery({ queryKey: ["analyses"], queryFn: getAnalyses });

  const uploadMutation = useMutation({
    mutationFn: createCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
      pushToast({ title: "Candidate uploaded", description: "The CV has been submitted successfully.", type: "success" });
      setShowUpload(false);
      setFormState({ full_name: "", email: "", phone_number: "" });
      setCvFile(null);
    },
    onError: (error: unknown) => pushToast({ title: "Upload failed", description: error instanceof Error ? error.message : "Unable to upload candidate.", type: "error" }),
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      queryClient.invalidateQueries({ queryKey: ["analyses"] });
      pushToast({ title: "Analysis complete", description: "Candidate analysis ran successfully.", type: "success" });
    },
    onError: (error: unknown) => pushToast({ title: "Analysis failed", description: error instanceof Error ? error.message : "Unable to run analysis.", type: "error" }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCandidate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["candidates"] });
      pushToast({ title: "Candidate deleted", description: "The candidate record was removed.", type: "success" });
    },
    onError: (error: unknown) => pushToast({ title: "Delete failed", description: error instanceof Error ? error.message : "Unable to delete candidate.", type: "error" }),
  });

  const candidates = Array.isArray(candidatesQuery.data) ? candidatesQuery.data : [];
  const analyses = Array.isArray(analysesQuery.data) ? analysesQuery.data : [];

  const filteredCandidates = useMemo(() => {
    return candidates.filter((candidate: any) => {
      const match = matchesSearch(candidate, search);
      const analyzed = Boolean(candidate.analysis_completed);
      const experience = Number(candidate.years_of_experience || 0);

      const analysisMatch =
        analysisFilter === "all" ||
        (analysisFilter === "analyzed" && analyzed) ||
        (analysisFilter === "not_analyzed" && !analyzed);

      const experienceMatch =
        experienceFilter === "all" ||
        (experienceFilter === "0-2" && experience <= 2) ||
        (experienceFilter === "3-5" && experience >= 3 && experience <= 5) ||
        (experienceFilter === "6+" && experience >= 6);

      return match && analysisMatch && experienceMatch;
    });
  }, [analysisFilter, candidates, experienceFilter, search]);

  const totalPages = Math.max(1, Math.ceil(filteredCandidates.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedCandidates = filteredCandidates.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const onSubmitUpload = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!cvFile) {
      pushToast({ title: "Missing CV file", description: "Please attach a PDF or DOCX file.", type: "error" });
      return;
    }

    const payload = new FormData();
    payload.append("full_name", formState.full_name);
    payload.append("email", formState.email);
    payload.append("phone_number", formState.phone_number);
    payload.append("cv_file", cvFile);
    uploadMutation.mutate(payload);
  };

  if (candidatesQuery.isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">Candidates</h2>
          <p className="mt-2 text-sm text-slate-500">Search, analyze, and manage candidate profiles.</p>
        </div>
        <button onClick={() => setShowUpload(true)} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-soft">
          Upload CV
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <label className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Search</div>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, email, skills" className="mt-2 w-full bg-transparent text-sm outline-none" />
        </label>
        <label className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Analysis</div>
          <select value={analysisFilter} onChange={(event) => setAnalysisFilter(event.target.value as any)} className="mt-2 w-full bg-transparent text-sm outline-none">
            <option value="all">All</option>
            <option value="analyzed">Analyzed</option>
            <option value="not_analyzed">Not analyzed</option>
          </select>
        </label>
        <label className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Experience</div>
          <select value={experienceFilter} onChange={(event) => setExperienceFilter(event.target.value as any)} className="mt-2 w-full bg-transparent text-sm outline-none">
            <option value="all">All</option>
            <option value="0-2">0-2 years</option>
            <option value="3-5">3-5 years</option>
            <option value="6+">6+ years</option>
          </select>
        </label>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-soft">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Results</div>
          <div className="mt-2 font-semibold text-slate-950">{filteredCandidates.length} candidates</div>
        </div>
      </div>

      {filteredCandidates.length ? (
        <section className="grid gap-6 lg:grid-cols-2">
          {pagedCandidates.map((candidate: any) => {
            const relatedAnalysis = analyses.find((analysis: any) => analysis.candidate === candidate.id);
            return (
              <CandidateCard
                key={candidate.id}
                id={candidate.id}
                fullName={candidate.full_name}
                email={candidate.email}
                skills={candidate.skills || []}
                yearsOfExperience={Number(candidate.years_of_experience || 0)}
                analysisCompleted={Boolean(candidate.analysis_completed)}
                matchScore={Number(relatedAnalysis?.match_score || 0)}
                href={`/candidates/${candidate.id}`}
                actions={
                  <>
                    <Link href={`/candidates/${candidate.id}`} className="rounded-2xl bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700">
                      View details
                    </Link>
                    <button onClick={() => analyzeMutation.mutate(candidate.id)} className="rounded-2xl bg-blue-600 px-3 py-2 text-xs font-medium text-white">
                      Run analysis
                    </button>
                    <button onClick={() => deleteMutation.mutate(candidate.id)} className="rounded-2xl bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                      Delete
                    </button>
                  </>
                }
              />
            );
          })}
        </section>
      ) : (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500 shadow-soft">No candidates match the current filters.</div>
      )}

      <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-soft">
        <div>
          Page {currentPage} of {totalPages}
        </div>
        <div className="flex gap-2">
          <button disabled={currentPage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="rounded-2xl bg-slate-100 px-3 py-2 disabled:opacity-40">
            Previous
          </button>
          <button disabled={currentPage >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className="rounded-2xl bg-slate-100 px-3 py-2 disabled:opacity-40">
            Next
          </button>
        </div>
      </div>

      <Modal open={showUpload} title="Upload Candidate CV" onClose={() => setShowUpload(false)}>
        <form className="space-y-4" onSubmit={onSubmitUpload}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Full name
              <input required value={formState.full_name} onChange={(event) => setFormState({ ...formState, full_name: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Email
              <input required type="email" value={formState.email} onChange={(event) => setFormState({ ...formState, email: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
          </div>
          <label className="block text-sm font-medium text-slate-700">
            Phone number
            <input value={formState.phone_number} onChange={(event) => setFormState({ ...formState, phone_number: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            CV file
            <input required type="file" accept=".pdf,.docx" onChange={(event) => setCvFile(event.target.files?.[0] || null)} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setShowUpload(false)} className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">Cancel</button>
            <button type="submit" className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
              {uploadMutation.isPending ? "Uploading..." : "Upload CV"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
