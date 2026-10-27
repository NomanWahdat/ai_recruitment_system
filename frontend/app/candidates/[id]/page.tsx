"use client";
import { useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getCandidateById, updateCandidate, analyzeCandidate, runMatch } from "@/services/candidateService";
import { listJobs } from "@/services/jobService";
import { getAnalyses } from "@/services/analysisService";
import { apiClient, errorMessage } from "@/lib/axios";
import type { Candidate, Application, Page } from "@/types/domain";
import { Modal } from "@/components/ui/Modal";
import { ScoreAudit } from "@/components/ui/ScoreAudit";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ResponseSourceBadge } from "@/components/ui/ResponseSourceBadge";

function ProfileEditor({candidate,onDone}:{candidate:Candidate;onDone:()=>void}) {
  const cache=useQueryClient();
  const [form,setForm]=useState({full_name:candidate.full_name,email:candidate.email,phone_number:candidate.phone_number,
    skills:candidate.skills.join(", "),years_of_experience:candidate.years_of_experience,education:candidate.education});
  const save=useMutation({mutationFn:()=>updateCandidate(candidate.id,{...form,skills:form.skills.split(",").map(s=>s.trim()).filter(Boolean)}),
    onSuccess:()=>{cache.invalidateQueries();onDone();}});
  return <form onSubmit={(event:FormEvent)=>{event.preventDefault();save.mutate();}} className="space-y-4">
    <p className="text-sm text-slate-600">Check these values against the source evidence. Saving records your review and queues fresh matches.</p>
    {Object.entries(form).map(([field,value])=><label key={field} className="block capitalize">{field.replaceAll("_"," ")}
      <input required={["full_name","email"].includes(field)} type={field==="email"?"email":field==="years_of_experience"?"number":"text"} min="0" max="60" step="0.1" value={value} onChange={e=>setForm({...form,[field]:e.target.value})} className="mt-2 w-full rounded-xl border p-3" /></label>)}
    {save.isError && <p role="alert" className="text-rose-700">{errorMessage(save.error)}</p>}
    <button disabled={save.isPending} className="rounded-xl bg-blue-600 px-4 py-3 text-white">Save reviewed profile</button>
  </form>;
}
function ApplicationReview({application}:{application:Application}) {
  const cache=useQueryClient(); const [note,setNote]=useState(""); const [stage,setStage]=useState("");
  const next:Record<string,string[]>={applied:["review","rejected"],review:["shortlisted","rejected"],shortlisted:["interview","rejected"],interview:["hired","rejected"],hired:[],rejected:["review"]};
  const save=useMutation({mutationFn:()=>apiClient.patch(`/applications/${application.id}/`,{stage,review_note:note}),onSuccess:()=>{cache.invalidateQueries();setNote("");setStage("");}});
  return <article className="rounded-xl border p-4"><h4 className="font-semibold">{application.job_title} · {application.stage}</h4>
    {application.review_note && <p className="mt-2 text-sm text-slate-600">Last review: {application.review_note}</p>}
    {!!next[application.stage]?.length && <form onSubmit={e=>{e.preventDefault();save.mutate();}} className="mt-4 flex flex-wrap gap-3">
      <select required aria-label="Next application stage" value={stage} onChange={e=>setStage(e.target.value)} className="rounded border p-2"><option value="">Choose next stage</option>{next[application.stage].map(value=><option key={value}>{value}</option>)}</select>
      <input required aria-label="Human review note" value={note} onChange={e=>setNote(e.target.value)} maxLength={1000} placeholder="Evidence supporting your decision" className="min-w-56 flex-1 rounded border p-2" />
      <button disabled={save.isPending} className="rounded bg-blue-600 px-3 py-2 text-white">Record decision</button>
    </form>}
    {save.isError && <p role="alert" className="mt-2 text-rose-700">{errorMessage(save.error)}</p>}
    <details className="mt-4"><summary>Decision history ({application.decisions.length})</summary>{application.decisions.map(decision=><p key={decision.id} className="mt-2 text-sm">{decision.from_stage} → {decision.to_stage}: {decision.note} · Reviewer #{decision.reviewer} · {new Date(decision.created_at).toLocaleString()}</p>)}</details>
  </article>;
}

export default function CandidateDetailPage() {
  const id=Number(useParams<{id:string}>().id); const cache=useQueryClient();
  const [replacementFile,setReplacementFile]=useState<File|null>(null);
  const [edit,setEdit]=useState(false); const [jobSearch,setJobSearch]=useState(""); const [jobId,setJobId]=useState("");
  const candidate=useQuery({queryKey:["candidate",id],queryFn:()=>getCandidateById(id),refetchInterval:5000});
  const jobs=useQuery({queryKey:["jobs","select",jobSearch],queryFn:()=>listJobs({search:jobSearch})});
  const analyses=useQuery({queryKey:["analyses","candidate",id],queryFn:()=>getAnalyses({candidate:id}),refetchInterval:5000});
  const applications=useQuery({queryKey:["applications",id],queryFn:async()=>(await apiClient.get<Page<Application>>("/applications/",{params:{candidate:id}})).data});
  const match=useMutation({mutationFn:()=>runMatch(id,Number(jobId)),onSuccess:()=>cache.invalidateQueries()});
  const retry=useMutation({mutationFn:()=>analyzeCandidate(id),onSuccess:()=>cache.invalidateQueries()});
  const replace=useMutation({mutationFn:async()=>{const form=new FormData();if(replacementFile)form.append("cv_file",replacementFile);return apiClient.patch(`/candidates/${id}/`,form);},onSuccess:()=>{cache.invalidateQueries();setReplacementFile(null);}});
  const apply=useMutation({mutationFn:()=>apiClient.post("/applications/",{candidate:id,job:Number(jobId)}),onSuccess:()=>cache.invalidateQueries()});
  if(candidate.isPending)return <LoadingSpinner />;
  if(candidate.isError)return <p role="alert">{errorMessage(candidate.error)}</p>;
  const data=candidate.data;
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-3xl font-semibold">{data.full_name}</h2><p className="mt-2 text-slate-500">{data.email} · {data.processing_status}</p></div>
      <div className="flex flex-wrap gap-3"><button onClick={()=>setEdit(true)} className="rounded-xl bg-blue-600 px-4 py-3 text-white">Review / correct profile</button>
        <button disabled={retry.isPending} onClick={()=>retry.mutate()} className="rounded-xl border bg-white px-4 py-3">{data.processing_status==="failed"?"Retry extraction":"Refresh matches"}</button>
        {data.cv_download_url && <a href={data.cv_download_url} className="rounded-xl border bg-white px-4 py-3">Download private CV</a>}</div>
    </div>
    {data.extraction_error||data.analysis_error ? <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-800">{data.extraction_error||data.analysis_error}</div>:null}
    {(retry.isError||match.isError||apply.isError||replace.isError) && <p role="alert" className="text-rose-700">{errorMessage(retry.error||match.error||apply.error||replace.error)}</p>}
    <form onSubmit={event=>{event.preventDefault();replace.mutate();}} className="flex flex-wrap items-end gap-3 rounded-xl border bg-white p-4"><label className="block text-sm">Replace source document<input aria-label="Replacement resume" type="file" accept=".pdf,.docx" onChange={event=>setReplacementFile(event.target.files?.[0]||null)} className="mt-2 block"/></label><button disabled={!replacementFile||replace.isPending} className="rounded-xl border px-4 py-2 disabled:opacity-40">Replace and queue extraction</button><p className="w-full text-xs text-slate-500">Replacing a document clears the previous review and invalidates old matches.</p></form>
    <div className="grid gap-6 xl:grid-cols-3">
      <section className="rounded-2xl border bg-white p-6 xl:col-span-2"><h3 className="text-xl font-semibold">Extracted profile and evidence</h3>
        <p className="mt-2 text-sm text-slate-500">{data.profile_reviewed_at?"Human-reviewed profile":"Unreviewed extraction — verify before shortlisting"}</p>
        <dl className="mt-5 space-y-5">{Object.entries({skills:data.skills.join(", "),experience:data.years_of_experience+" years",education:data.education,phone:data.phone_number}).map(([field,value])=><div key={field}><dt className="text-sm font-semibold capitalize">{field}</dt><dd className="mt-1">{value||"Not found"}</dd></div>)}</dl>
        <div className="mt-6 space-y-3">{Object.entries(data.evidence||{}).map(([field,lines])=><details key={field} className="rounded-xl bg-slate-50 p-3"><summary className="cursor-pointer capitalize">{field.replaceAll("_"," ")} · {lines.length} source lines</summary>
          {lines.map(line=><p key={line.line} className="mt-2 whitespace-pre-wrap text-sm text-slate-600">Line {line.line}: {line.text}</p>)}</details>)}</div>
      </section>
      <aside className="rounded-2xl border bg-white p-6"><h3 className="font-semibold">Source resume text</h3><pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap text-sm text-slate-600">{data.extracted_text||"No extracted text available."}</pre>
        <p className="mt-4 text-xs text-slate-500">Retention until {data.retention_until?new Date(data.retention_until).toLocaleDateString():"not set"}.</p></aside>
    </div>
    <section className="rounded-2xl border bg-white p-6"><h3 className="text-xl font-semibold">Job-specific comparison</h3><p className="mt-2 text-sm text-slate-500">Scores are advisory. Human application stages are managed separately.</p>
      <div className="mt-4 flex flex-wrap gap-3"><input aria-label="Find job" placeholder="Filter jobs" value={jobSearch} onChange={e=>setJobSearch(e.target.value)} className="rounded-xl border p-3" />
        <select aria-label="Select job" value={jobId} onChange={e=>setJobId(e.target.value)} className="rounded-xl border p-3"><option value="">Choose a job</option>{jobs.data?.results.map(job=><option key={job.id} value={job.id}>{job.title}</option>)}</select>
        <button disabled={!jobId||match.isPending} onClick={()=>match.mutate()} className="rounded-xl bg-blue-600 px-4 py-3 text-white disabled:opacity-40">Run matching</button>
        <button disabled={!jobId||apply.isPending} onClick={()=>apply.mutate()} className="rounded-xl border px-4 py-3 disabled:opacity-40">Create application</button>
      </div>
      <div className="mt-6 space-y-4">{analyses.data?.map(analysis=><article key={analysis.id} className="rounded-xl border p-4"><p className="font-semibold">Job #{analysis.job} · {analysis.match_score}% {analysis.is_stale?"? Refresh required":""}</p>
        <div className="mt-2"><ScoreBar value={analysis.match_score}/></div><div className="mt-3"><ResponseSourceBadge source={analysis.provider} model={analysis.provider_model} reason={analysis.generation_provenance?.scoring?.fallback_reason}/></div>
        {analysis.insufficient_requirements && <p role="status" className="mt-2 text-amber-800">Define job criteria before comparing this candidate. The score is not informative.</p>}
        <p className="mt-3 text-sm">Matched: {analysis.matched_skills.join(", ")||"None"} · Missing: {analysis.missing_skills.join(", ")||"None"}</p>
        <details className="mt-3"><summary>Score components · {analysis.scoring_version}</summary><pre className="mt-2 overflow-auto text-xs">{JSON.stringify(analysis.score_components,null,2)}</pre></details><ScoreAudit key={analysis.scoring_snapshot?.sha256 || analysis.id} analysis={analysis}/></article>)}</div>
    </section>
    <section className="space-y-4 rounded-2xl border bg-white p-6"><h3 className="text-xl font-semibold">Human review and applications</h3>
      {applications.data?.results.map(application=><ApplicationReview key={application.id} application={application}/>)}{!applications.data?.count && <p>Create an application for a selected job to begin the review workflow.</p>}
    </section>
    <Modal open={edit} title="Review extracted profile" onClose={()=>setEdit(false)}>{edit && <ProfileEditor candidate={data} onDone={()=>setEdit(false)}/>}</Modal>
  </div>;
}
