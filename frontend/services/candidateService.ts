import { apiClient } from "@/lib/axios";

export async function getCandidates() {
  const response = await apiClient.get("/candidates/");
  return response.data;
}

export async function getCandidateById(id: number) {
  const response = await apiClient.get(`/candidates/${id}/`);
  return response.data;
}

export async function createCandidate(payload: FormData) {
  const response = await apiClient.post("/candidates/", payload, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteCandidate(id: number) {
  const response = await apiClient.delete(`/candidates/${id}/`);
  return response.data;
}

export async function analyzeCandidate(id: number) {
  const response = await apiClient.post(`/candidates/${id}/analyze/`);
  return response.data;
}

export async function runMatch(candidateId: number, jobId: number) {
  const response = await apiClient.post("/match/", { candidate_id: candidateId, job_id: jobId });
  return response.data;
}
