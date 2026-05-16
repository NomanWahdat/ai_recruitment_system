import { apiClient } from "@/lib/axios";

export async function getJobs() {
  const response = await apiClient.get("/jobs/");
  return response.data;
}

export async function getJobById(id: number) {
  const response = await apiClient.get(`/jobs/${id}/`);
  return response.data;
}

export async function createJob(payload: Record<string, unknown>) {
  const response = await apiClient.post("/jobs/", payload);
  return response.data;
}

export async function deleteJob(id: number) {
  const response = await apiClient.delete(`/jobs/${id}/`);
  return response.data;
}

export async function getJobRankings(jobId: number) {
  const response = await apiClient.get(`/jobs/${jobId}/rankings/`);
  return response.data;
}

export async function runMatchingEngine() {
  const response = await apiClient.post("/automation/reprocess/");
  return response.data;
}
