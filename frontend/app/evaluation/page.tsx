"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getEvaluation } from "@/services/analysisService";
import { errorMessage } from "@/lib/axios";
import { downloadJson } from "@/lib/download";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function EvaluationPage() {
  const [split, setSplit] = useState("all");
  const query = useQuery({queryKey: ["evaluation"], queryFn: getEvaluation});
  if (query.isPending) return <LoadingSpinner />;
  if (query.isError) return <p role="alert" className="text-red-700">{errorMessage(query.error)}</p>;
  const report = query.data;
  const group = split === "all" ? report : report.by_split[split];
  const failures = report.failure_cases.filter(row => split === "all" || row.split === split);
  return <div className="space-y-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h2 className="text-2xl font-semibold">Accuracy evaluation</h2><p className="mt-2 text-sm text-slate-600">Measure extraction errors and compare ranking methods on labelled examples.</p></div>
      <button onClick={() => downloadJson("evaluation-report.json", report)} className="rounded-xl border bg-white px-4 py-3">Download evaluation report</button>
    </div>
    <div role="note" className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
      <p className="font-semibold">Synthetic benchmark, not independent hiring evidence.</p>
      <p className="mt-2">The labels were authored with the project. Challenge cases expose known limitations. Independent recruiter labels and representative resumes are still needed to measure real-world accuracy.</p>
    </div>
    <section className="rounded-2xl border bg-white p-5">
      <label className="text-sm font-medium">Dataset split <select aria-label="Evaluation split" value={split} onChange={event => setSplit(event.target.value)} className="ml-3 rounded-lg border p-2"><option value="all">All examples</option>{Object.keys(report.by_split).map(name => <option key={name} value={name}>{name}</option>)}</select></label>
      <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[ ["Labelled examples", String(group.records)], ["Email exact match", percent(group.email_accuracy)], ["Skill micro F1", percent(group.skill_f1)], ["Experience mean absolute error", `${group.experience_mae_years.toFixed(2)} years`] ].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-4"><p className="text-sm text-slate-600">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}
      </div>
      <p className="mt-4 text-sm text-slate-600">Skill precision {percent(group.skill_precision)}; recall {percent(group.skill_recall)}. Precision penalizes invented skills; recall penalizes missed skills.</p>
      {split === "all" && <p className="mt-2 text-xs text-slate-500">95% bootstrap interval for skill F1: {report.confidence_intervals_95.skill_f1.map(percent).join(" to ")}. This interval describes this small corpus, not general hiring validity.</p>}
    </section>
    <section className="rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Ranking comparison</h3>
      <p className="mt-2 text-sm text-slate-600">NDCG rewards putting strongly labelled matches first. Recall measures how many relevant examples appear in the top {report.k}. MRR measures how soon the first relevant example appears. Higher values are better.</p>
      <div className="mt-4 overflow-auto"><table className="w-full text-left text-sm"><thead><tr>{["Job", "Method", `NDCG@${report.k}`, `Recall@${report.k}`, "MRR"].map(label => <th key={label} scope="col" className="border-b p-3">{label}</th>)}</tr></thead><tbody>
        {Object.entries(group.ranking).flatMap(([job, methods]) => Object.entries(methods).map(([method, metrics]) => <tr key={`${job}-${method}`}><td className="border-b p-3">{job}</td><td className="border-b p-3">{method.replaceAll("_", " ")}</td><td className="border-b p-3">{metrics.ndcg_at_k.toFixed(4)}</td><td className="border-b p-3">{metrics.recall_at_k === null ? "No relevant labels" : metrics.recall_at_k.toFixed(4)}</td><td className="border-b p-3">{metrics.mrr.toFixed(4)}</td></tr>))}
      </tbody></table></div>
    </section>
    <section className="rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Failure examples ({failures.length})</h3>
      <p className="mt-2 text-sm text-slate-600">These are measured extraction errors. Cases are retained in the benchmark so limitations remain visible.</p>
      {failures.length ? <div className="mt-4 space-y-3">{failures.map(row => <article key={row.id} className="rounded-xl border p-4 text-sm"><h4 className="font-semibold">{row.id} / {row.category}</h4><p className="mt-2">Unexpected skills: {row.unexpected_skills.join(", ") || "none"}. Missed skills: {row.missing_skills.join(", ") || "none"}.</p><p>Experience error: {row.experience_absolute_error.toFixed(1)} years. Email match: {row.email_correct ? "correct" : "incorrect"}.</p></article>)}</div> : <p className="mt-4 text-sm">No extraction errors measured in this split.</p>}
    </section>
    <section className="space-y-3 rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Reproduction and limits</h3>
      <p className="text-sm">Dataset {report.dataset_version}; experience reference date {report.as_of_date}; external requests {report.external_requests}. {report.mode}.</p>
      <p className="text-sm">Cross-split identical documents: {report.cross_split_duplicate_documents}. Independent human agreement: {report.independent_human_agreement ? report.independent_human_agreement.quadratic_weighted_kappa?.toFixed(3) ?? "undefined" : "not measured"}.</p>
      <p className="text-sm">Regression checks: {report.checks.passed ? "passed" : "failed"} ({report.checks.split}). {report.checks.scope}</p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">{report.limitations.map(text => <li key={text}>{text}</li>)}</ul>
      <details><summary className="cursor-pointer text-sm">Dataset and implementation fingerprints</summary><p className="mt-2 break-all font-mono text-xs">Dataset: {report.dataset_sha256}<br/>Implementation: {report.implementation_sha256}</p></details>
    </section>
  </div>;
}
