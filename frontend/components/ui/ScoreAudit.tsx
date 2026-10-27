"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { Analysis } from "@/types/domain";
import { getScoreRuns, verifyScore } from "@/services/analysisService";
import { errorMessage } from "@/lib/axios";
import { downloadJson } from "@/lib/download";

export function ScoreAudit({analysis}: {analysis: Analysis}) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [page, setPage] = useState(1);
  const history = useQuery({queryKey: ["score-runs", analysis.id, page], queryFn: () => getScoreRuns(analysis.id, page), enabled: historyOpen});
  const verification = useMutation({mutationFn: (run: number | undefined) => verifyScore(analysis.id, run)});
  const snapshot = analysis.scoring_snapshot;
  const saved = snapshot && "schema_version" in snapshot && snapshot.schema_version ? snapshot : null;
  return <div className="mt-4 space-y-3 rounded-xl bg-slate-50 p-4">
    <h4 className="font-semibold">Reproducible score</h4>
    {saved ? <>
      <p className="text-sm">Local {saved.rubric.score.toFixed(2)} + AI {saved.ai.score === null ? "not used" : saved.ai.score.toFixed(2)}; applied AI weight {(saved.ai.applied_weight * 100).toFixed(0)}%.</p>
      <p className="font-mono text-sm">{saved.rubric.score} x (1 - {saved.ai.applied_weight}) + {saved.ai.score ?? 0} x {saved.ai.applied_weight} = {saved.final_score}</p>
      <p className="text-xs text-slate-600">Profile revision {saved.inputs.candidate.revision ?? "unknown"}; job revision {saved.inputs.job.revision ?? "unknown"}. Saved {new Date(saved.calculated_at).toLocaleString()}.</p>
      <div className="flex flex-wrap gap-3">
        <button disabled={verification.isPending} onClick={() => verification.mutate(undefined)} className="rounded-lg border bg-white px-3 py-2 text-sm disabled:opacity-50">Verify saved score</button>
        <button onClick={() => downloadJson(`score-${analysis.id}.json`, saved)} className="rounded-lg border bg-white px-3 py-2 text-sm">Download score snapshot</button>
      </div>
      <details className="text-sm"><summary className="cursor-pointer">Saved inputs, weights and fingerprint</summary><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(saved, null, 2)}</pre></details>
    </> : <p className="text-sm text-amber-800">This older result has no scoring snapshot. Run matching again to save a reproducible score.</p>}
    <p className="text-xs text-slate-600">Verification replays saved arithmetic without calling AI. A fingerprint detects accidental changes; it is not a digital signature.</p>
    <button aria-expanded={historyOpen} onClick={() => setHistoryOpen(!historyOpen)} className="rounded-lg border bg-white px-3 py-2 text-sm">{historyOpen ? "Hide score history" : "Show score history"}</button>
    {historyOpen && <div className="space-y-2">
      {history.isPending && <p className="text-sm">Loading history...</p>}
      {history.isError && <p role="alert" className="text-sm text-red-700">{errorMessage(history.error)}</p>}
      {history.data?.results.map(run => <div key={run.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm">
        <span>Run #{run.id}: {run.snapshot.final_score.toFixed(2)} / 100; {run.snapshot.ai.provider}; {new Date(run.created_at).toLocaleString()}</span>
        <button disabled={verification.isPending} onClick={() => verification.mutate(run.id)} className="rounded-lg border bg-white px-3 py-1">Verify run #{run.id}</button>
      </div>)}
      {history.data?.count === 0 && <p className="text-sm">No saved scoring runs yet.</p>}
      <div className="flex gap-3"><button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous runs</button><button disabled={!history.data?.next} onClick={() => setPage(page + 1)}>Next runs</button></div>
    </div>}
    {verification.isPending && <p role="status" className="text-sm">Verifying saved arithmetic...</p>}
    {verification.isError && <p role="alert" className="text-sm text-red-700">{errorMessage(verification.error)}</p>}
    {verification.data && <p role="status" className={`text-sm ${verification.data.verified ? "text-green-800" : "text-red-700"}`}>{verification.data.verified ? `Verified: reproduced ${verification.data.reproduced_score} / 100. No AI request made.` : verification.data.reason}</p>}
  </div>;
}
