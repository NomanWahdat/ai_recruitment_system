"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { reprocessAutomation, rerunMatchingEngine } from "@/services/automationService";
import { ResponseSourceBadge } from "@/components/ui/ResponseSourceBadge";
import { useToast } from "@/components/ui/Toast";

function extractSources(data: any): string[] {
  const sources: string[] = [];
  if (!data) return sources;
  // Top-level response_source
  if (data.response_source) sources.push(data.response_source);
  // From candidate_results events
  for (const cr of data.candidate_results || []) {
    for (const ev of cr.events || []) {
      const a = ev.analysis || ev;
      if (a.matching_response_source) sources.push(a.matching_response_source);
      if (a.explanation_response_source) sources.push(a.explanation_response_source);
    }
  }
  // From job_results events
  for (const jr of data.job_results || []) {
    for (const ev of jr.events || []) {
      if (ev.parsed?.response_source) sources.push(ev.parsed.response_source);
      if (ev.matching_response_source) sources.push(ev.matching_response_source);
    }
  }
  // From matching results
  for (const r of data.results || []) {
    for (const m of r.matches || []) {
      if (m.response_source) sources.push(m.response_source);
    }
  }
  return sources;
}

function overallSource(data: any): string | null {
  const sources = extractSources(data);
  if (!sources.length) return null;
  return sources.some((s) => s.includes("groq_ai")) ? "groq_ai" : "local";
}

export default function AutomationPage() {
  const { pushToast } = useToast();
  const [logs, setLogs] = useState<Array<{ label: string; detail: string; source: string | null }>>([]);
  const [lastResult, setLastResult] = useState<any>(null);

  const appendLog = (label: string, detail: string, source: string | null) => {
    setLogs((current) => [{ label, detail, source }, ...current].slice(0, 12));
  };

  const reprocessMutation = useMutation({
    mutationFn: reprocessAutomation,
    onSuccess: (data) => {
      setLastResult(data);
      const src = overallSource(data);
      appendLog(
        "Reprocess All Candidates",
        `Candidates: ${data?.candidates ?? 0}, Jobs: ${data?.jobs ?? 0}`,
        src,
      );
      pushToast({ title: "Automation reprocessed", description: "All workflows completed successfully.", type: "success" });
    },
    onError: () => pushToast({ title: "Automation failed", description: "Unable to reprocess workflows.", type: "error" }),
  });

  const matchingMutation = useMutation({
    mutationFn: rerunMatchingEngine,
    onSuccess: (data) => {
      setLastResult(data);
      const src = data?.response_source || overallSource(data);
      appendLog(
        "Re-run Matching Engine",
        `Jobs: ${data?.jobs_processed ?? 0}, Candidates: ${data?.candidates_processed ?? 0}`,
        src,
      );
      pushToast({ title: "Matching rerun complete", description: "The matching engine executed successfully.", type: "success" });
    },
    onError: () => pushToast({ title: "Matching rerun failed", description: "Unable to rerun matching engine.", type: "error" }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">Automation</h2>
        <p className="mt-2 text-sm text-slate-500">Trigger full workflow reprocessing and review execution logs.</p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button onClick={() => reprocessMutation.mutate()} className="rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white shadow-soft transition hover:bg-indigo-700">
          {reprocessMutation.isPending ? "Running..." : "Reprocess All Candidates"}
        </button>
        <button onClick={() => matchingMutation.mutate()} className="rounded-2xl bg-white px-5 py-3 text-sm font-medium text-slate-700 shadow-soft ring-1 ring-slate-200 transition hover:bg-slate-50">
          {matchingMutation.isPending ? "Running..." : "Re-run Matching Engine"}
        </button>
      </div>

      <section className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft xl:col-span-2">
          <div className="text-lg font-semibold text-slate-950">Workflow Logs</div>
          <div className="mt-4 space-y-3">
            {logs.length ? logs.map((log, index) => (
              <div key={`${log.label}-${index}`} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-slate-900">{log.label}</div>
                  {log.source && <ResponseSourceBadge source={log.source} />}
                </div>
                <div className="mt-1 text-slate-500">{log.detail}</div>
              </div>
            )) : <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">No automation logs yet.</div>}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex items-center justify-between">
            <div className="text-lg font-semibold text-slate-950">Latest Result</div>
            {lastResult && <ResponseSourceBadge source={overallSource(lastResult)} />}
          </div>
          <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-600">{lastResult ? JSON.stringify(lastResult, null, 2) : "Trigger a workflow to see results here."}</pre>
        </div>
      </section>
    </div>
  );
}
