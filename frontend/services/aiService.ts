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
