"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createJob, deleteJob, getJobs } from "@/services/jobService";
import { parseJob } from "@/services/aiService";
import { JobCard } from "@/components/ui/JobCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";

const PAGE_SIZE = 6;

function normalizeSkills(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function JobsPage() {
  const queryClient = useQueryClient();
  const { pushToast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [parsedJob, setParsedJob] = useState<any>(null);
  const [formState, setFormState] = useState({
    title: "",
    company_name: "",
    location: "",
    description: "",
    required_skills: "",
    minimum_experience: "",
    education_requirement: "",
  });

  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: getJobs });

  const createMutation = useMutation({
    mutationFn: createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      pushToast({ title: "Job created", description: "The new role is now active in the dashboard.", type: "success" });
      setShowCreate(false);
      setFormState({ title: "", company_name: "", location: "", description: "", required_skills: "", minimum_experience: "", education_requirement: "" });
    },
    onError: (error: unknown) => {
      let message = "Unable to create job.";
      try {
        // Axios error with response body will contain validation details
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const err: any = error;
        if (err?.response?.data) {
          const data = err.response.data;
          if (typeof data === "string") message = data;
          else if (data.detail) message = data.detail;
          else message = JSON.stringify(data);
        } else if (error instanceof Error) {
          message = error.message;
        }
      } catch (_e) {
        // fallback
      }
      pushToast({ title: "Create failed", description: message, type: "error" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      pushToast({ title: "Job deleted", description: "The job record was removed.", type: "success" });
    },
    onError: (error: unknown) => pushToast({ title: "Delete failed", description: error instanceof Error ? error.message : "Unable to delete job.", type: "error" }),
  });

  const parseMutation = useMutation({
    mutationFn: parseJob,
    onSuccess: (data) => {
      setParsedJob(data);
      pushToast({ title: "Job parsed", description: "AI job insights generated.", type: "success" });
    },
    onError: (error: unknown) => pushToast({ title: "Parse failed", description: error instanceof Error ? error.message : "Unable to parse job.", type: "error" }),
  });

  const jobs = Array.isArray(jobsQuery.data) ? jobsQuery.data : [];

  const filteredJobs = useMemo(() => {
    return jobs.filter((job: any) => {
      const text = `${job.title || ""} ${job.company_name || ""} ${(job.required_skills || []).join(" ")}`.toLowerCase();
      return text.includes(search.toLowerCase());
    });
  }, [jobs, search]);

  const totalPages = Math.max(1, Math.ceil(filteredJobs.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedJobs = filteredJobs.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const onSubmitCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate({
      ...formState,
      required_skills: normalizeSkills(formState.required_skills),
      minimum_experience: Number(formState.minimum_experience || 0),
    });
  };

  if (jobsQuery.isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">Jobs</h2>
          <p className="mt-2 text-sm text-slate-500">Create jobs, parse descriptions, and navigate into rankings.</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-soft">
          Create Job
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-soft md:col-span-2">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Search</div>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Title, company, skills" className="mt-2 w-full bg-transparent text-sm outline-none" />
        </label>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-soft">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Results</div>
          <div className="mt-2 font-semibold text-slate-950">{filteredJobs.length} jobs</div>
        </div>
      </div>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="grid gap-6 lg:grid-cols-2 xl:col-span-2">
          {pagedJobs.length ? pagedJobs.map((job: any) => (
            <JobCard
              key={job.id}
              id={job.id}
              title={job.title}
              companyName={job.company_name}
              location={job.location}
              experience={Number(job.minimum_experience || 0)}
              skills={job.required_skills || []}
              href={`/jobs/${job.id}`}
              actions={
                <>
                  <Link href={`/jobs/${job.id}`} className="rounded-2xl bg-slate-100 px-3 py-2 text-xs font-medium text-slate-700">View details</Link>
                  <Link href={`/rankings?job=${job.id}`} className="rounded-2xl bg-blue-50 px-3 py-2 text-xs font-medium text-blue-700">View rankings</Link>
                  <button onClick={() => parseMutation.mutate(job.description || "")} className="rounded-2xl bg-white px-3 py-2 text-xs font-medium text-slate-700 ring-1 ring-slate-200">Parse using AI</button>
                  <button onClick={() => deleteMutation.mutate(job.id)} className="rounded-2xl bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">Delete</button>
                </>
              }
            />
          )) : <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-sm text-slate-500 shadow-soft">No jobs match the current search.</div>}
        </div>

        <div className="space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">AI Parsed Insights</div>
            <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-600">{parsedJob ? JSON.stringify(parsedJob, null, 2) : "Parse a job to see AI insights here."}</pre>
          </section>

          <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="text-lg font-semibold text-slate-950">Pagination</div>
            <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
              <span>Page {currentPage} of {totalPages}</span>
              <div className="flex gap-2">
                <button disabled={currentPage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} className="rounded-2xl bg-slate-100 px-3 py-2 disabled:opacity-40">Prev</button>
                <button disabled={currentPage >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} className="rounded-2xl bg-slate-100 px-3 py-2 disabled:opacity-40">Next</button>
              </div>
            </div>
          </section>
        </div>
      </section>

      <Modal open={showCreate} title="Create Job" onClose={() => setShowCreate(false)}>
        <form className="space-y-4" onSubmit={onSubmitCreate}>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Job title
              <input required value={formState.title} onChange={(event) => setFormState({ ...formState, title: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Company name
              <input required value={formState.company_name} onChange={(event) => setFormState({ ...formState, company_name: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">
              Location
              <input value={formState.location} onChange={(event) => setFormState({ ...formState, location: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
            <label className="block text-sm font-medium text-slate-700">
              Experience required
              <input value={formState.minimum_experience} onChange={(event) => setFormState({ ...formState, minimum_experience: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
            </label>
          </div>
          <label className="block text-sm font-medium text-slate-700">
            Required skills (comma separated)
            <input value={formState.required_skills} onChange={(event) => setFormState({ ...formState, required_skills: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Education requirement
            <input value={formState.education_requirement} onChange={(event) => setFormState({ ...formState, education_requirement: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            Description
            <textarea required rows={6} value={formState.description} onChange={(event) => setFormState({ ...formState, description: event.target.value })} className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          </label>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setShowCreate(false)} className="rounded-2xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">Cancel</button>
            <button type="submit" className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
              {createMutation.isPending ? "Creating..." : "Create Job"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
