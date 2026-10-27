"use client";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listCandidates, createCandidate, bulkUpload, deleteCandidate } from "@/services/candidateService";
import { errorMessage } from "@/lib/axios";
import { Modal } from "@/components/ui/Modal";
import { Pagination } from "@/components/ui/Pagination";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export default function CandidatesPage() {
  const cache=useQueryClient();
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
    <div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-2xl font-semibold">Candidates</h2><p className="mt-2 text-slate-500">Private resumes, extraction evidence, and human review.</p></div>
      <button onClick={()=>setShowUpload(true)} className="rounded-xl bg-blue-600 px-4 py-2 text-white">Upload CVs</button></div>
    <div className="flex flex-wrap gap-3"><input aria-label="Search candidates" value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}} placeholder="Search name, email, skills" className="min-w-64 rounded-xl border p-3" />
      <select aria-label="Processing status" value={status} onChange={e=>{setStatus(e.target.value);setPage(1);}} className="rounded-xl border p-3">{["","pending","processing","completed","failed"].map(s=><option key={s} value={s}>{s||"All processing states"}</option>)}</select><input aria-label="Minimum experience" type="number" min="0" max="60" step="0.1" value={minimum} placeholder="Min years" onChange={e=>{setMinimum(e.target.value);setPage(1);}} className="w-32 rounded-xl border p-3"/><input aria-label="Maximum experience" type="number" min="0" max="60" step="0.1" value={maximum} placeholder="Max years" onChange={e=>{setMaximum(e.target.value);setPage(1);}} className="w-32 rounded-xl border p-3"/></div>
    {upload.isSuccess && <div role="status" className="rounded-xl bg-blue-50 p-4">Upload accepted for processing. {upload.data.results && <pre className="overflow-auto text-xs">{JSON.stringify(upload.data.results,null,2)}</pre>}</div>}
    {(candidates.isError||remove.isError) && <p role="alert" className="text-rose-700">{errorMessage(candidates.error||remove.error)}</p>}
    {candidates.isPending && <LoadingSpinner />}
    <div className="grid gap-5 md:grid-cols-2">{candidates.data?.results.map(candidate=><article key={candidate.id} className="rounded-2xl border bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><Link className="text-lg font-semibold text-blue-800" href={`/candidates/${candidate.id}`}>{candidate.full_name}</Link><span className={candidate.processing_status==="failed"?"text-rose-700":"text-slate-600"}>{candidate.processing_status}</span></div>
      <p className="mt-2 text-sm text-slate-500">{candidate.email} · {candidate.years_of_experience} years</p>
      <div className="mt-4 flex flex-wrap gap-2">{candidate.skills.map(skill=><span key={skill} className="rounded-full bg-blue-50 px-3 py-1 text-xs">{skill}</span>)}</div>
      <p className="mt-4 text-sm">{candidate.profile_reviewed_at?"Profile reviewed by recruiter":"Profile needs human review"}</p>
      <div className="mt-4 flex gap-4"><Link className="text-blue-700" href={`/candidates/${candidate.id}`}>Review evidence →</Link>
        <button disabled={remove.isPending} onClick={()=>{if(window.confirm("Delete this candidate, resume, applications and analyses?"))remove.mutate(candidate.id);}} className="text-rose-700">Delete</button></div>
    </article>)}</div>
    {candidates.data && !candidates.data.count && <p>No candidates found. Upload a text-based PDF or DOCX.</p>}
    <Pagination page={page} count={candidates.data?.count||0} onChange={setPage} />
    <Modal open={showUpload} title="Upload resumes" onClose={()=>setShowUpload(false)}>
      <form onSubmit={submit} className="space-y-4">
        <p>PDF or DOCX ? 10 MB each ? Up to 10 files. Duplicate documents are detected within your account.</p>
        <label className="block">Resume files<input required type="file" accept=".pdf,.docx" multiple onChange={e=>setFiles(Array.from(e.target.files||[]))} className="mt-2 block w-full rounded border p-3" /></label>
        {files.length<=1 && <><label className="block">Name (optional before extraction)<input value={name} onChange={e=>setName(e.target.value)} className="mt-2 w-full rounded border p-3" /></label>
          <label className="block">Email (optional before extraction)<input type="email" value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 w-full rounded border p-3" /></label></>}
        {upload.isError && <p role="alert" className="text-rose-700">{errorMessage(upload.error)}</p>}
        <button disabled={!files.length||files.length>10||upload.isPending} className="rounded-xl bg-blue-600 px-4 py-3 text-white disabled:opacity-40">{upload.isPending?"Uploading?":"Queue extraction"}</button>
      </form>
    </Modal>
  </div>;
}
