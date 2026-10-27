"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { listJobs,getJobRankings } from "@/services/jobService";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { errorMessage } from "@/lib/axios";
interface Ranking {candidate_id:number;candidate_name:string;match_score:number;ranking_position:number;matched_skills:string[];provider:string}
export default function RankingsPage() {
  const params=useSearchParams();const [jobId,setJobId]=useState(params.get("job")||"");const [search,setSearch]=useState("");
  const jobs=useQuery({queryKey:["jobs","ranking-select",search],queryFn:()=>listJobs({search})});
  useEffect(()=>{if(!jobId&&jobs.data?.results.length)setJobId(String(jobs.data.results[0].id));},[jobs.data,jobId]);
  const ranking=useQuery<{top_candidates:Ranking[]}>({queryKey:["rankings",jobId],enabled:!!jobId,queryFn:()=>getJobRankings(Number(jobId)),refetchInterval:5000});
  return <div className="space-y-6"><h2 className="text-2xl font-semibold">Job-specific rankings</h2><p className="text-slate-600">Current results only. Equal scores use candidate ID as a stable tie-break. Review evidence before making decisions.</p>
    <div className="flex flex-wrap gap-3"><input aria-label="Search jobs for ranking" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Filter jobs" className="rounded-xl border p-3"/>
      <select aria-label="Ranking job" value={jobId} onChange={e=>setJobId(e.target.value)} className="rounded-xl border p-3"><option value="">Select a job</option>{jobs.data?.results.map(job=><option key={job.id} value={job.id}>{job.title}</option>)}</select></div>
    {(jobs.isError||ranking.isError)&&<p role="alert">{errorMessage(jobs.error||ranking.error)}</p>}
    <div className="space-y-4">{ranking.data?.top_candidates.map(row=><article key={row.candidate_id} className="rounded-2xl border bg-white p-6">
      <div className="flex justify-between gap-3"><Link className="text-lg font-semibold text-blue-800" href={`/candidates/${row.candidate_id}`}>#{row.ranking_position} {row.candidate_name}</Link><span>{row.match_score}%</span></div>
      <div className="mt-3"><ScoreBar value={row.match_score}/></div><p className="mt-3 text-sm text-slate-600">Matched evidence: {row.matched_skills.join(", ")||"None"}</p><p className="mt-2 text-xs">Source: {row.provider}</p>
    </article>)}</div>{ranking.data&&!ranking.data.top_candidates.length&&<p>No current matches. Process candidates or refresh this job.</p>}
  </div>;
}
