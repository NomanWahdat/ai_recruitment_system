"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createJob, deleteJob, listJobs } from "@/services/jobService";
import { errorMessage } from "@/lib/axios";
import { JobCard } from "@/components/ui/JobCard";
import { JobForm } from "@/components/ui/JobForm";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";
import { Pagination } from "@/components/ui/Pagination";

export default function JobsPage() {
  const cache = useQueryClient(); const router = useRouter();
  const [search,setSearch] = useState(""); const [page,setPage] = useState(1); const [create,setCreate] = useState(false);
  useEffect(() => {const params = new URLSearchParams(window.location.search); if (params.get("new") === "1") setCreate(true);}, []);
  const jobs = useQuery({queryKey: ["jobs", page, search], queryFn: () => listJobs({page, search})});
  const save = useMutation({mutationFn: createJob, onSuccess: job => {cache.invalidateQueries({queryKey: ["jobs"]}); setCreate(false); router.push(`/jobs/${job.id}`);}});
  const remove = useMutation({mutationFn: deleteJob, onSuccess: () => cache.invalidateQueries({queryKey: ["jobs"]})});
  return <div className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-2xl font-semibold">Jobs</h2><p className="mt-2 text-slate-600">Open a role to add resumes, compare candidates and continue hiring.</p></div><button onClick={() => setCreate(true)} className="rounded-xl bg-blue-600 px-5 py-3 font-medium text-white">Create job</button></div>
    <label className="block max-w-xl text-sm font-medium">Find a job<input value={search} onChange={event => {setSearch(event.target.value); setPage(1);}} placeholder="Job title, company or skill" className="mt-2 w-full rounded-xl border bg-white p-3"/></label>
    {(jobs.isError || remove.isError) && <p role="alert" className="text-rose-700">{errorMessage(jobs.error || remove.error)}</p>}{jobs.isPending && <LoadingSpinner/>}
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{jobs.data?.results.map(job => <JobCard key={job.id} title={job.title} companyName={job.company_name} location={job.location} experience={job.minimum_experience} skills={job.required_skills} href={`/jobs/${job.id}`} actions={<><Link href={`/jobs/${job.id}`} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white">Open job</Link><details className="relative text-sm"><summary className="cursor-pointer rounded-lg border px-3 py-2">More options</summary><div className="mt-2 flex flex-wrap gap-3"><Link href={`/rankings?job=${job.id}`} className="text-blue-700">Compare candidates</Link><button onClick={() => {if (window.confirm("Delete this job and its applications, comparisons and score history?")) remove.mutate(job.id);}} className="text-rose-700">Delete job</button></div></details></>}/>)}</div>
    {jobs.data && !jobs.data.count && <div className="rounded-2xl border border-dashed bg-white p-8"><h3 className="font-semibold">{search ? "No matching jobs" : "Create your first job"}</h3><p className="mt-2 text-sm text-slate-600">{search ? "Try another title or skill." : "Add the role's requirements, then start comparing resumes."}</p></div>}
    <Pagination page={page} count={jobs.data?.count || 0} onChange={setPage}/>
    <Modal open={create} title="Create a job" onClose={() => setCreate(false)}>{create && <JobForm onSave={data => save.mutate(data)} pending={save.isPending} error={save.error}/>}</Modal>
  </div>;
}
