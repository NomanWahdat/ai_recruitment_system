"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { listCandidates } from "@/services/candidateService";
import { listJobs } from "@/services/jobService";
import { checkAIConnection, getAIStatus, getInterviewQuestions, getMatchExplanation, parseJob } from "@/services/aiService";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ResponseSourceBadge } from "@/components/ui/ResponseSourceBadge";
import { useToast } from "@/components/ui/Toast";

export default function AIToolsPage() {
  const { pushToast } = useToast();
  const providerQuery = useQuery({ queryKey: ["ai-status"], queryFn: getAIStatus });
  const connectionTest = useMutation({ mutationFn: checkAIConnection });
  const [jobDescription, setJobDescription] = useState("");
  const [jobParseResult, setJobParseResult] = useState<any>(null);
  const [explainCandidateId, setExplainCandidateId] = useState<number | "">("");
  const [explainJobId, setExplainJobId] = useState<number | "">("");
  const [interviewCandidateId, setInterviewCandidateId] = useState<number | "">("");
  const [interviewJobId, setInterviewJobId] = useState<number | "">("");
  const [matchExplanation, setMatchExplanation] = useState<any>(null);
  const [questionsResult, setQuestionsResult] = useState<any>(null);

  const [candidateSearch,setCandidateSearch]=useState("");
  const [jobSearch,setJobSearch]=useState("");
  const candidatesQuery = useQuery({ queryKey: ["candidates","ai-select",candidateSearch], queryFn: async () => (await listCandidates({search:candidateSearch})).results });
  const jobsQuery = useQuery({ queryKey: ["jobs","ai-select",jobSearch], queryFn: async () => (await listJobs({search:jobSearch})).results });

  useEffect(() => {
    const candidates = Array.isArray(candidatesQuery.data) ? candidatesQuery.data : [];
    const jobs = Array.isArray(jobsQuery.data) ? jobsQuery.data : [];
    if (!explainCandidateId && candidates.length) setExplainCandidateId(candidates[0].id);
    if (!interviewCandidateId && candidates.length) setInterviewCandidateId(candidates[0].id);
    if (!explainJobId && jobs.length) setExplainJobId(jobs[0].id);
    if (!interviewJobId && jobs.length) setInterviewJobId(jobs[0].id);
  }, [candidatesQuery.data, jobsQuery.data, explainCandidateId, explainJobId, interviewCandidateId, interviewJobId]);

  const parseMutation = useMutation({
    mutationFn: parseJob,
    onSuccess: (data) => {
      setJobParseResult(data);
      pushToast({ title: "Job parsed", description: "Structured job insights are ready.", type: "success" });
    },
    onError: () => pushToast({ title: "Parse failed", description: "Unable to parse the job description.", type: "error" }),
  });

  const explanationMutation = useMutation({
    mutationFn: () => getMatchExplanation(Number(explainCandidateId), Number(explainJobId)),
    onSuccess: (data) => {
      setMatchExplanation(data);
      pushToast({ title: "Match explanation ready", description: data.response_source === "local" ? "Local rubric explanation generated." : "AI explanation generated.", type: "success" });
    },
    onError: () => pushToast({ title: "Explanation failed", description: "Unable to explain the match.", type: "error" }),
  });

  const interviewMutation = useMutation({
    mutationFn: () => getInterviewQuestions(Number(interviewCandidateId), Number(interviewJobId)),
    onSuccess: (data) => {
      setQuestionsResult(data);
      pushToast({ title: "Interview questions ready", description: "Question set generated successfully.", type: "success" });
    },
    onError: () => pushToast({ title: "Question generation failed", description: "Unable to generate questions.", type: "error" }),
  });

  if (candidatesQuery.isLoading || jobsQuery.isLoading) return <LoadingSpinner />;

  const candidates = Array.isArray(candidatesQuery.data) ? candidatesQuery.data : [];
  const jobs = Array.isArray(jobsQuery.data) ? jobsQuery.data : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-950">AI Tools</h2>
        <p className="mt-2 text-sm text-slate-500">Generate job insights, match explanations, and interview questions.</p>
      </div>

      <section aria-label="AI connection" className="rounded-3xl border border-slate-200 bg-white p-6">
        <h3 className="font-semibold text-slate-950">AI connection</h3>
        {providerQuery.isPending && <p className="mt-2 text-sm">Checking configuration...</p>}
        {providerQuery.isError && <p role="alert" className="mt-2 text-sm text-red-700">Unable to load AI configuration. Check the API connection.</p>}
        {providerQuery.data && <>
          <p className="mt-2 text-sm text-slate-600">{providerQuery.data.available ? "A provider is configured. Test the connection to verify access." : "AI is unavailable. Local rules will be used until a provider is configured."}</p>
          <ul className="mt-3 space-y-2 text-sm">
            {providerQuery.data.providers.map(provider => <li key={provider.provider}>
              <span className="font-medium capitalize">{provider.provider}</span>: {provider.message}
            </li>)}
          </ul>
          <p className="mt-3 text-sm text-slate-600">{providerQuery.data.scoring_enabled ? "Matching can blend a validated AI score with the local rubric." : "Matching uses the local rubric. AI-assisted scoring is a separate setting."} Resume extraction uses local parsing rules and needs human review.</p>
        </>}
        <p className="mt-3 text-xs text-slate-500">The connection test sends only a synthetic job description. No candidate data is sent.</p>
        <button disabled={connectionTest.isPending || !providerQuery.data?.available} onClick={() => connectionTest.mutate()} className="mt-3 rounded-xl bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">
          {connectionTest.isPending ? "Testing connection..." : "Test AI connection"}
        </button>
        {connectionTest.data && <div role="status" className="mt-3">
          <p className="mb-2 text-sm">{connectionTest.data.ok ? "AI connection verified." : "AI connection failed. Local rules remain available."}</p>
          <ResponseSourceBadge source={connectionTest.data.response_source} model={connectionTest.data.model} reason={connectionTest.data.fallback_reason} />
        </div>}
        {connectionTest.isError && <p role="alert" className="mt-3 text-sm text-red-700">Unable to complete the test. Check the API connection or try again later.</p>}
      </section>

      <div className="flex flex-wrap gap-3"><input aria-label="Filter AI tool candidates" placeholder="Find candidate" value={candidateSearch} onChange={e=>setCandidateSearch(e.target.value)} className="rounded-xl border p-3"/><input aria-label="Filter AI tool jobs" placeholder="Find job" value={jobSearch} onChange={e=>setJobSearch(e.target.value)} className="rounded-xl border p-3"/></div>
      <div className="grid gap-6 xl:grid-cols-3">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="text-lg font-semibold text-slate-950">Job Parser</div>
          <textarea value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} rows={8} placeholder="Paste a job description" className="mt-4 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm leading-6" />
          <button onClick={() => parseMutation.mutate(jobDescription)} className="mt-4 rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
            Parse Job
          </button>
          {jobParseResult && <div className="mt-3"><ResponseSourceBadge source={jobParseResult?.response_source} model={jobParseResult?.model} reason={jobParseResult?.fallback_reason} /></div>}
          <pre className="mt-4 overflow-auto rounded-2xl bg-slate-50 p-4 text-xs leading-6 text-slate-600">{jobParseResult ? JSON.stringify({skills: jobParseResult.skills, role_type: jobParseResult.role_type, experience_level: jobParseResult.experience_level, summary: jobParseResult.summary}, null, 2) : "No parsed output yet."}</pre>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="text-lg font-semibold text-slate-950">Match Explainer</div>
          <div className="mt-4 space-y-4">
            <select value={explainCandidateId} onChange={(event) => setExplainCandidateId(Number(event.target.value))} className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm">
              {candidates.map((candidate: any) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
            </select>
            <select value={explainJobId} onChange={(event) => setExplainJobId(Number(event.target.value))} className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm">
              {jobs.map((job: any) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <button onClick={() => explanationMutation.mutate()} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
              Explain Match
            </button>
          </div>
          {matchExplanation && <div className="mt-3"><ResponseSourceBadge source={matchExplanation?.response_source} model={matchExplanation?.model} reason={matchExplanation?.fallback_reason} /></div>}
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <div><div className="font-medium text-slate-900">Summary</div><div className="mt-1 whitespace-pre-wrap">{matchExplanation?.summary || "No explanation generated yet."}</div></div>
            <div><div className="font-medium text-slate-900">Strengths</div><div className="mt-1">{(matchExplanation?.strengths || []).join("; ") || "-"}</div></div>
            <div><div className="font-medium text-slate-900">Weaknesses</div><div className="mt-1">{(matchExplanation?.weaknesses || []).join("; ") || "-"}</div></div>
            <div><div className="font-medium text-slate-900">Recommendation</div><div className="mt-1">{matchExplanation?.recommendation || "-"}</div></div>
          </div>
        </section>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
          <div className="text-lg font-semibold text-slate-950">Interview Generator</div>
          <div className="mt-4 space-y-4">
            <select value={interviewCandidateId} onChange={(event) => setInterviewCandidateId(Number(event.target.value))} className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm">
              {candidates.map((candidate: any) => <option key={candidate.id} value={candidate.id}>{candidate.full_name}</option>)}
            </select>
            <select value={interviewJobId} onChange={(event) => setInterviewJobId(Number(event.target.value))} className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm">
              {jobs.map((job: any) => <option key={job.id} value={job.id}>{job.title}</option>)}
            </select>
            <button onClick={() => interviewMutation.mutate()} className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-medium text-white">
              Generate Questions
            </button>
          </div>
          {questionsResult && <div className="mt-3"><ResponseSourceBadge source={questionsResult?.response_source} model={questionsResult?.model} reason={questionsResult?.fallback_reason} /></div>}
          <div className="mt-4 space-y-4 text-sm text-slate-700">
            <div><div className="font-medium text-slate-900">Technical</div><ul className="mt-1 list-disc space-y-1 pl-5">{(questionsResult?.technical_questions || []).map((question: string, index: number) => <li key={index}>{question}</li>) || null}</ul></div>
            <div><div className="font-medium text-slate-900">Behavioral</div><ul className="mt-1 list-disc space-y-1 pl-5">{(questionsResult?.behavioral_questions || []).map((question: string, index: number) => <li key={index}>{question}</li>) || null}</ul></div>
            <div><div className="font-medium text-slate-900">Skill-based</div><ul className="mt-1 list-disc space-y-1 pl-5">{(questionsResult?.skill_based_questions || []).map((question: string, index: number) => <li key={index}>{question}</li>) || null}</ul></div>
          </div>
        </section>
      </div>
    </div>
  );
}
