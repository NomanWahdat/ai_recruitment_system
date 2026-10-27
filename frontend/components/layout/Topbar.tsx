"use client";
import { useDeferredValue, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { listCandidates } from "@/services/candidateService";
import { listJobs } from "@/services/jobService";

export function Topbar() {
  const {user,logout} = useAuth();
  const [search,setSearch] = useState("");
  const deferred = useDeferredValue(search.trim());
  const [error,setError] = useState("");
  const results = useQuery({queryKey:["global-search",deferred],enabled:deferred.length>=2,
    queryFn:async () => {const [candidates,jobs] = await Promise.all([listCandidates({search:deferred}),listJobs({search:deferred})]); return {candidates:candidates.results.slice(0,4),jobs:jobs.results.slice(0,4)};}});
  return <header className="flex flex-wrap items-center justify-between gap-4 border-b bg-white px-6 py-4">
    <div><p className="text-sm text-slate-500">Recruiter workspace</p><h1 className="text-xl font-semibold">{user?.full_name}</h1></div>
    <div className="relative"><input aria-label="Global search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search your candidates and jobs" className="w-64 rounded-xl border px-3 py-2" />
      {deferred.length>=2 && <div className="absolute right-0 z-30 mt-2 w-72 rounded-xl border bg-white p-3 shadow-lg">
        {results.isPending && <p>Searching...</p>}
        {results.isError && <p role="alert">Search unavailable.</p>}
        {results.data?.candidates.map(c=><Link onClick={()=>setSearch("")} className="block rounded p-2 hover:bg-blue-50" key={`c${c.id}`} href={`/candidates/${c.id}`}>{c.full_name}</Link>)}
        {results.data?.jobs.map(j=><Link onClick={()=>setSearch("")} className="block rounded p-2 hover:bg-blue-50" key={`j${j.id}`} href={`/jobs/${j.id}`}>{j.title}</Link>)}
        {results.data && !results.data.candidates.length && !results.data.jobs.length && <p>No results.</p>}
      </div>}
    </div>
    <button onClick={()=>logout().catch(()=>setError("Sign-out failed. Try again."))} className="rounded-xl border px-3 py-2">Sign out</button>
    {error && <p role="alert">{error}</p>}
  </header>;
}
