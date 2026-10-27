"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobById,updateJob,runMatchingEngine } from "@/services/jobService";
import { errorMessage } from "@/lib/axios";
import type { Job } from "@/types/domain";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Modal } from "@/components/ui/Modal";

function JobEditor({job,done}:{job:Job;done:()=>void}) {
  const cache=useQueryClient();
  const [form,setForm]=useState({employment_type:job.employment_type,salary_range:job.salary_range,title:job.title,company_name:job.company_name,location:job.location,description:job.description,
    required_skills:job.required_skills.join(", "),minimum_experience:String(job.minimum_experience),education_requirement:job.education_requirement});
  const [weights,setWeights]=useState({skills:job.scoring_weights.skills??0.5,experience:job.scoring_weights.experience??0.3,education:job.scoring_weights.education??0.2});
  const save=useMutation({mutationFn:()=>updateJob(job.id,{...form,minimum_experience:Number(form.minimum_experience),
    required_skills:form.required_skills.split(",").map(s=>s.trim()).filter(Boolean),scoring_weights:weights}),
    onSuccess:()=>{cache.invalidateQueries();done();}});
  return <form onSubmit={event=>{event.preventDefault();save.mutate();}} className="space-y-4">
    {Object.entries(form).map(([field,value])=><label key={field} className="block capitalize">{field.replaceAll("_"," ")}
      {field==="description"?<textarea required value={value} onChange={e=>setForm({...form,[field]:e.target.value})} className="mt-2 w-full rounded border p-3" rows={5}/>:field==="employment_type"?<select value={value} onChange={e=>setForm({...form,[field]:e.target.value})} className="mt-2 w-full rounded border p-3">{["full_time","part_time","contract","internship","remote"].map(type=><option key={type}>{type}</option>)}</select>:<input required={["title","company_name"].includes(field)} value={value} type={field==="minimum_experience"?"number":"text"} min="0" onChange={e=>setForm({...form,[field]:e.target.value})} className="mt-2 w-full rounded border p-3"/>}</label>)}
    <fieldset className="rounded-xl border p-4"><legend>Scoring weights ? total must equal 1</legend><div className="grid grid-cols-3 gap-3">{Object.entries(weights).map(([field,value])=><label key={field} className="capitalize">{field}<input type="number" min="0" max="1" step="0.05" value={value} onChange={e=>setWeights({...weights,[field]:Number(e.target.value)})} className="mt-2 w-full rounded border p-2"/></label>)}</div></fieldset>
    {save.isError&&<p role="alert" className="text-rose-700">{errorMessage(save.error)}</p>}
    <button disabled={save.isPending} className="rounded-xl bg-blue-600 px-4 py-3 text-white">Save job and refresh matches</button>
  </form>;
}
export default function JobDetailPage() {
  const id=Number(useParams<{id:string}>().id);const [edit,setEdit]=useState(false);const cache=useQueryClient();
  const query=useQuery({queryKey:["job",id],queryFn:()=>getJobById(id)});
  const match=useMutation({mutationFn:()=>runMatchingEngine(id),onSuccess:()=>cache.invalidateQueries()});
  if(query.isPending)return <LoadingSpinner/>;
  if(query.isError)return <p role="alert">{errorMessage(query.error)}</p>;
  const job=query.data;
  return <div className="space-y-6"><div className="flex flex-wrap justify-between gap-3"><div><h2 className="text-3xl font-semibold">{job.title}</h2><p className="mt-2 text-slate-500">{job.company_name} · {job.location}</p></div>
    <div className="flex flex-wrap gap-3"><button onClick={()=>setEdit(true)} className="rounded-xl border bg-white px-4 py-3">Edit job / criteria</button>
      <button disabled={match.isPending} onClick={()=>match.mutate()} className="rounded-xl bg-blue-600 px-4 py-3 text-white">Refresh this job?s matches</button></div></div>
    {match.isSuccess&&<p role="status">Matching queued for this job only. Track progress in Automation.</p>}
    {match.isError&&<p role="alert">{errorMessage(match.error)}</p>}
    <section className="rounded-2xl border bg-white p-6"><h3 className="text-xl font-semibold">Requirements</h3><p className="mt-4 whitespace-pre-wrap">{job.description}</p><p className="mt-5">Skills: {job.required_skills.join(", ")||"Not specified"}</p>
      <p className="mt-3">Minimum experience: {job.minimum_experience} years</p><p className="mt-3">Education: {job.education_requirement||"Not specified"}</p>
      <p className="mt-3">Weights: {JSON.stringify(job.scoring_weights)} {Object.keys(job.scoring_weights).length?"":"(defaults: skills 0.5, experience 0.3, education 0.2)"}</p></section>
    <Link href={`/rankings?job=${id}`} className="inline-block rounded-xl bg-blue-50 px-4 py-3 text-blue-800">View current candidate ranking →</Link>
    <Modal open={edit} title="Edit job requirements" onClose={()=>setEdit(false)}>{edit&&<JobEditor job={job} done={()=>setEdit(false)}/>}</Modal>
  </div>;
}
