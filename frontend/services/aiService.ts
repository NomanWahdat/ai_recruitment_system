import { apiClient } from "@/lib/axios";

export async function parseJob(jobDescription: string) {
  const response = await apiClient.post("/ai/parse-job/", { job_description: jobDescription });
  return response.data;
}

export async function getMatchExplanation(candidateId: number, jobId: number) {
  const response = await apiClient.post("/ai/match-explanation/", { candidate_id: candidateId, job_id: jobId });
  return response.data;
}

export async function getInterviewQuestions(candidateId: number, jobId: number) {
  const response = await apiClient.post("/ai/interview-questions/", { candidate_id: candidateId, job_id: jobId });
  return response.data;
}

export type AIStatus = {
  available: boolean;
  verified: boolean;
  scoring_enabled: boolean;
  providers: {provider: string; model: string; enabled: boolean; status: string; message: string}[];
};

export type AIConnectionResult = {
  ok: boolean;
  response_source: string;
  model: string;
  fallback_reason: string;
};

export async function getAIStatus(): Promise<AIStatus> {
  return (await apiClient.get("/ai/status/")).data;
}

export async function checkAIConnection(): Promise<AIConnectionResult> {
  return (await apiClient.post("/ai/check/", {})).data;
}
