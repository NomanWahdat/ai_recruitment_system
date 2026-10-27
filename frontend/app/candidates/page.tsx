"use client";
import Link from "next/link";
import { useDeferredValue, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listCandidates, createCandidate, bulkUpload, deleteCandidate } from "@/services/candidateService";
import { getJobById } from "@/services/jobService";
import { processingLabels, readableEmail } from "@/lib/recruiter";
import { errorMessage, validationMessage } from "@/lib/axios";
import { Modal } from "@/components/ui/Modal";
import { Pagination } from "@/components/ui/Pagination";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function CandidatesPage() {
  const cache=useQueryClient();
  const [jobId,setJobId]=useState("");
  useEffect(()=>{const params=new URLSearchParams(window.location.search);if(params.get("upload")==="1")setShowUpload(true);const job=params.get("job");if(job&&/^\d+$/.test(job))setJobId(job);},[]);
  const contextJob=useQuery({queryKey:["job",Number(jobId)],queryFn:()=>getJobById(Number(jobId)),enabled:!!jobId});
  const [search,setSearch]=useState(""); const query=useDeferredValue(search);
  const [minimum,setMinimum]=useState(""); const [maximum,setMaximum]=useState("");
  const [page,setPage]=useState(1); const [status,setStatus]=useState("");
  const [showUpload,setShowUpload]=useState(false); const [files,setFiles]=useState<File[]>([]);
  const [name,setName]=useState(""); const [email,setEmail]=useState("");
  const candidates=useQuery({queryKey:["candidates",page,query,status,minimum,maximum],queryFn:()=>listCandidates({page,search:query,processing_status:status,...(minimum!==""?{min_experience:minimum}:{}),...(maximum!==""?{max_experience:maximum}:{})}),refetchInterval:5000});
  const upload=useMutation({mutationFn:async()=> {
    if(files.length>1) return bulkUpload(files);
    const data=new FormData(); data.append("cv_file",files[0]); data.append("full_name",name||files[0].name.split(".")[0]); data.append("email",email||"unknown@example.invalid");
    return createCandidate(data);
  },onSuccess:()=>{cache.invalidateQueries();setShowUpload(false);setFiles([]);}});
  const remove=useMutation({mutationFn:deleteCandidate,onSuccess:()=>cache.invalidateQueries()});
  const submit=(event:FormEvent)=>{event.preventDefault();if(files.length)upload.mutate();};
  return <div className="space-y-6">
    <div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-2xl font-semibold">Candidates</h2><p className="mt-2 text-slate-500">Add resumes, check the details, and continue reviewing candidates.</p></div>
      <button onClick={()=>setShowUpload(true)} className="rounded-xl bg-blue-600 px-4 py-2 text-white">Upload resumes</button></div>
    {contextJob.data && <div className="rounded-xl bg-blue-50 p-4 text-sm text-blue-900">You are working on <Link href={`/jobs/${jobId}`} className="font-semibold underline">{contextJob.data.title}</Link>. Resumes join your private candidate pool; this job will be selected when you open a profile.</div>}
    <div className="flex flex-wrap gap-3"><input aria-label="Search candidates" value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}} placeholder="Search name, email, skills" className="min-w-64 rounded-xl border p-3" />
      <select aria-label="Processing status" value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}} className="rounded-xl border p-3">{["","pending","processing","completed","failed"].map(s=><option key={s} value={s}>{s ? processingLabels[s] : "All resume statuses"}</option>)}</select><details className="rounded-xl border bg-white p-3 text-sm"><summary className="cursor-pointer">Experience filters</summary><div className="mt-3 flex flex-wrap gap-3"><input aria-label="Minimum experience" type="number" min="0" max="60" step="0.1" value={minimum} placeholder="Min years" onChange={e=>{setMinimum(e.target.value);setPage(1);}} className="w-32 rounded-xl border p-3"/><input aria-label="Maximum experience" type="number" min="0" max="60" step="0.1" value={maximum} placeholder="Max years" onChange={e=>{setMaximum(e.target.value);setPage(1);}} className="w-32 rounded-xl border p-3"/></div></details></div>
    {upload.isSuccess && <div role="status" className="space-y-2 rounded-xl bg-blue-50 p-4 text-sm"><p>{upload.data.results ? `${upload.data.queued_count} files accepted; ${upload.data.failed_count} need attention.` : "Resume uploaded. We will read the file and prepare the details for you to check."}</p>{upload.data.results && <ul className="space-y-1">{upload.data.results.map((item: {filename?:string;error?:unknown;candidate_id?:number},index:number)=><li key={index}>{item.filename || `Resume ${index+1}`}: {validationMessage(item.error) || "Accepted for processing"}</li>)}</ul>}<Link href="/automation" className="inline-block text-blue-700 underline">View processing activity</Link></div>}
    {(candidates.isError||remove.isError) && <p role="alert" className="text-rose-700">{errorMessage(candidates.error||remove.error)}</p>}
    {candidates.isPending && <LoadingSpinner />}
    <div className="grid gap-5 md:grid-cols-2">{candidates.data?.results.map(candidate=><article key={candidate.id} className="rounded-2xl border bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><Link className="text-lg font-semibold text-blue-800" href={`/candidates/${candidate.id}${jobId ? `?job=${jobId}` : ""}`}>{candidate.full_name}</Link><span className={candidate.processing_status==="failed"?"text-rose-700":"text-slate-600"}>{processingLabels[candidate.processing_status] || candidate.processing_status}</span></div>
      <p className="mt-2 text-sm text-slate-500">{readableEmail(candidate.email)} · {candidate.years_of_experience} years</p>
      <div className="mt-4 flex flex-wrap gap-2">{candidate.skills.map(skill=><span key={skill} className="rounded-full bg-blue-50 px-3 py-1 text-xs">{skill}</span>)}</div>
      <p className="mt-4 text-sm">{candidate.profile_reviewed_at?"Details checked":"Check these details before deciding"}</p>
      <div className="mt-4 flex gap-4"><Link className="text-blue-700" href={`/candidates/${candidate.id}${jobId ? `?job=${jobId}` : ""}`}>Review evidence →</Link>
        <details><summary className="cursor-pointer text-sm text-slate-500">More options</summary><button disabled={remove.isPending} onClick={()=>{if(window.confirm("Delete this candidate, resume, applications and analyses?"))remove.mutate(candidate.id);}} className="mt-2 text-rose-700">Delete candidate</button></details></div>
    </article>)}</div>
    {candidates.data && !candidates.data.count && <p>No candidates found. Upload a text-based PDF or DOCX.</p>}
    <Pagination page={page} count={candidates.data?.count||0} onChange={setPage} />
    <Modal open={showUpload} title="Upload resumes" onClose={()=>setShowUpload(false)}>
      <form onSubmit={submit} className="space-y-4">
        <p>Upload up to 10 PDF or DOCX resumes, 10 MB each. We will check for duplicate files and read them in the background.</p>
        <label className="block">Resume files<input required type="file" accept=".pdf,.docx" multiple onChange={e=>setFiles(Array.from(e.target.files||[]))} className="mt-2 block w-full rounded border p-3" /></label>
        {files.length<=1 && <details><summary className="cursor-pointer text-sm">Add name and email manually (optional)</summary><label className="block">Name (optional before extraction)<input value={name} onChange={e=>setName(e.target.value)} className="mt-2 w-full rounded border p-3" /></label>
          <label className="block">Email (optional before extraction)<input type="email" value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 w-full rounded border p-3" /></label></details>}
        {files.length > 10 && <p role="alert" className="text-sm text-rose-700">Choose no more than 10 resumes at a time.</p>}
        {upload.isError && <p role="alert" className="text-rose-700">{errorMessage(upload.error)}</p>}
        <button disabled={!files.length||files.length>10||upload.isPending} className="rounded-xl bg-blue-600 px-4 py-3 text-white disabled:opacity-40">{upload.isPending?"Uploading...":"Upload and read resumes"}</button>
      </form>
    </Modal>
  </div>;
}
