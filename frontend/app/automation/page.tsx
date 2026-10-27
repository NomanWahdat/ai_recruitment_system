"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, errorMessage } from "@/lib/axios";
import type { Page, Task } from "@/types/domain";
import { reprocessAutomation, rerunMatchingEngine } from "@/services/automationService";

export default function AutomationPage() {
  const cache=useQueryClient();
  const tasks=useQuery({queryKey:["tasks"],queryFn:async()=>(await apiClient.get<Page<Task>>("/tasks/")).data,refetchInterval:3000});
  const action=useMutation({mutationFn:async(url:string)=>(await apiClient.post(url)).data,
    onSuccess:()=>{cache.invalidateQueries();}});
  const queue=useMutation({mutationFn:(kind:string)=>kind==="profiles"?reprocessAutomation():rerunMatchingEngine(),
    onSuccess:()=>{cache.invalidateQueries();}});
  return <div className="space-y-6"><h2 className="text-2xl font-semibold">Persistent processing tasks</h2>
    <p className="text-slate-600">Tasks survive web-server restarts. Failed tasks need an explicit retry; worker crashes are recovered after a lease expires.</p>
    <div className="flex flex-wrap gap-3"><button disabled={queue.isPending} onClick={()=>queue.mutate("profiles")} className="rounded-xl bg-blue-600 px-4 py-3 text-white">Queue profile processing</button>
      <button disabled={queue.isPending} onClick={()=>queue.mutate("matches")} className="rounded-xl border bg-white px-4 py-3">Queue matching for my jobs</button></div>
    {queue.isSuccess && <p role="status">{queue.data.queued} tasks queued. Completion is tracked below.</p>}
    {(action.isError||queue.isError||tasks.isError) && <p role="alert" className="text-rose-700">{errorMessage(action.error||queue.error||tasks.error)}</p>}
    <div className="space-y-3">{tasks.data?.results.map(task=><article key={task.id} className="rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold">Task #{task.id} · {task.kind}</h3><span className={task.status==="failed"?"text-rose-700":"text-blue-700"}>{task.status}</span></div>
      <p className="mt-2 text-sm text-slate-600">Candidate {task.candidate||"?"} · Job {task.job||"?"} · Attempts {task.attempts}</p>
      {task.error && <p className="mt-2 text-rose-700">{task.error}</p>}
      {task.status==="failed" && <button disabled={action.isPending} onClick={()=>action.mutate(`/tasks/${task.id}/retry/`)} className="mt-3 rounded-lg border px-3 py-2">Retry task</button>}
    </article>)}</div>
    {tasks.data?.count===0 && <p>No tasks yet.</p>}
  </div>;
}
