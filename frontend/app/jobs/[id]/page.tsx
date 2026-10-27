"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobById, updateJob, runMatchingEngine } from "@/services/jobService";
import { apiClient, errorMessage } from "@/lib/axios";
import type { Task } from "@/types/domain";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { JobForm } from "@/components/ui/JobForm";
import { CandidateMatches } from "@/components/ui/CandidateMatches";
import { HiringSteps } from "@/components/ui/HiringSteps";

export default function JobDetailPage() {
  const id = Number(useParams<{id: string}>().id); const cache = useQueryClient();
  const [edit,setEdit] = useState(false); const [tab,setTab] = useState("candidates");
  const query = useQuery({queryKey: ["job", id], queryFn: () => getJobById(id)});
  const save = useMutation({mutationFn: (data: Record<string, unknown>) => updateJob(id, data), onSuccess: () => {cache.invalidateQueries(); setEdit(false);}});
  const match = useMutation({mutationFn: () => runMatchingEngine(id)});
  const progress = useQuery<Task>({queryKey: ["job-matching-task", match.data?.id], queryFn: async () => (await apiClient.get(`/tasks/${match.data.id}/`)).data, enabled: !!match.data?.id, refetchInterval: query => ["completed", "failed"].includes(query.state.data?.status || "") ? false : 2000});
  useEffect(() => {if (progress.data?.status === "completed") cache.invalidateQueries({queryKey: ["rankings"]});}, [progress.data?.status, cache]);
  if (query.isPending) return <LoadingSpinner/>;
  if (query.isError) return <p role="alert">{errorMessage(query.error)}</p>;
  const job = query.data;
  const processing = match.isPending || (!!match.data && (!progress.data || ["queued", "running"].includes(progress.data.status)));
  return <div className="space-y-6"><Link href="/jobs" className="text-sm text-blue-700">Back to jobs</Link><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-3xl font-semibold">{job.title}</h2><p className="mt-2 text-slate-500">{job.company_name}{job.location ? ` / ${job.location}` : ""}</p></div><Link href={`/candidates?upload=1&job=${id}`} className="rounded-xl bg-blue-600 px-5 py-3 font-medium text-white">Add resumes</Link></div>
    <HiringSteps current={tab === "requirements" ? 0 : 3}/>
    <div className="flex flex-wrap gap-2 border-b" aria-label="Job workspace">{[["candidates", "Candidate matches"], ["requirements", "Job requirements"]].map(([value,label]) => <button key={value} aria-pressed={tab === value} onClick={() => setTab(value)} className={`border-b-2 px-4 py-3 text-sm font-medium ${tab === value ? "border-blue-600 text-blue-800" : "border-transparent text-slate-500"}`}>{label}</button>)}</div>
    {tab === "candidates" ? <section className="space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-xl font-semibold">Candidate matches</h3><p className="mt-1 text-sm text-slate-500">Scores help you compare requirements; you make the hiring decision.</p></div><button disabled={processing} onClick={() => match.mutate()} className="rounded-xl border bg-white px-4 py-2 text-sm disabled:opacity-50">{processing ? "Updating matches..." : "Update matches"}</button></div>
      {progress.data && <p role="status" className="rounded-xl bg-blue-50 p-3 text-sm text-blue-900">{progress.data.status === "completed" ? "Your comparisons are up to date." : progress.data.status === "failed" ? "We couldn't finish updating these matches. Open processing activity to try again." : "We're comparing your candidate pool with this job. You can keep working."} <Link href="/automation" className="underline">View progress</Link></p>}
      {(match.isError || progress.isError) && <p role="alert" className="text-rose-700">{errorMessage(match.error || progress.error)}</p>}<CandidateMatches jobId={id}/>
    </section> : <section className="space-y-4 rounded-2xl border bg-white p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-xl font-semibold">What this role needs</h3><button onClick={() => setEdit(true)} className="rounded-xl border px-4 py-2 text-sm">Edit requirements</button></div><p className="whitespace-pre-wrap text-sm leading-7 text-slate-600">{job.description}</p><dl className="grid gap-4 sm:grid-cols-2">{[["Required skills",job.required_skills.join(", ") || "Not specified"],["Experience",`${job.minimum_experience} years minimum`],["Education",job.education_requirement || "Not specified"]].map(([label,value]) => <div key={label} className="rounded-xl bg-slate-50 p-4"><dt className="text-sm font-semibold">{label}</dt><dd className="mt-2 text-sm text-slate-600">{value}</dd></div>)}</dl><details className="text-sm"><summary className="cursor-pointer">Additional details and matching priorities</summary><p className="mt-3">Employment: {job.employment_type.replaceAll("_", " ")}. Salary: {job.salary_range || "Not specified"}.</p><p className="mt-2">Priorities: {Object.keys(job.scoring_weights).length ? Object.entries(job.scoring_weights).map(([name,value]) => `${name} ${Math.round(value * 100)}%`).join(", ") : "Default matching priorities"}.</p><p className="mt-2 text-xs text-slate-500">Changing requirements makes older comparisons out of date and schedules new comparisons.</p></details></section>}
    <Modal open={edit} title="Edit job requirements" onClose={() => setEdit(false)}>{edit && <JobForm job={job} onSave={data => save.mutate(data)} pending={save.isPending} error={save.error}/>}</Modal>
  </div>;
}
