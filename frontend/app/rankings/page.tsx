"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listJobs } from "@/services/jobService";
import { CandidateMatches } from "@/components/ui/CandidateMatches";
import { AdvancedPageLink } from "@/components/ui/HiringSteps";
import { errorMessage } from "@/lib/axios";
export default function RankingsPage() {
  const params = useSearchParams(); const [jobId,setJobId] = useState(params.get("job") || ""); const [search,setSearch] = useState("");
  const jobs = useQuery({queryKey: ["jobs", "ranking-select", search], queryFn: () => listJobs({search})});
  useEffect(() => {if (!jobId && jobs.data?.results.length) setJobId(String(jobs.data.results[0].id));}, [jobs.data, jobId]);
  return <div className="space-y-6"><AdvancedPageLink/><div><h2 className="text-2xl font-semibold">Compare candidates across jobs</h2><p className="mt-2 text-slate-600">Choose a role to see its current candidate matches. The same comparisons are available inside each job.</p></div><div className="flex flex-wrap gap-3"><input aria-label="Search jobs for ranking" value={search} onChange={event => setSearch(event.target.value)} placeholder="Find a job" className="rounded-xl border p-3"/><select aria-label="Ranking job" value={jobId} onChange={event => setJobId(event.target.value)} className="rounded-xl border p-3"><option value="">Choose a job</option>{jobId && !jobs.data?.results.some(job => String(job.id) === jobId) && <option value={jobId}>Selected job</option>}{jobs.data?.results.map(job => <option key={job.id} value={job.id}>{job.title}</option>)}</select></div>{jobs.isError && <p role="alert">{errorMessage(jobs.error)}</p>}{jobId && <CandidateMatches jobId={Number(jobId)}/>}<details className="text-xs text-slate-500"><summary>How the list is ordered</summary><p className="mt-2">Only current results with usable requirements are included. Higher scores appear first; equal scores use the candidate record ID to keep ordering stable.</p></details></div>;
}
