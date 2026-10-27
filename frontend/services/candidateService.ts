import { apiClient } from "@/lib/axios";
import type { Candidate, Page } from "@/types/domain";
export async function listCandidates(params: Record<string, string | number> = {}): Promise<Page<Candidate>> { return (await apiClient.get("/candidates/", {params})).data; }
export async function getCandidates() { return (await listCandidates()).results; }
export async function getCandidateById(id: number): Promise<Candidate> { return (await apiClient.get(`/candidates/${id}/`)).data; }
export async function createCandidate(payload: FormData) { return (await apiClient.post("/candidates/", payload)).data; }
export async function bulkUpload(files: File[]) { const data = new FormData(); files.forEach(file => data.append("files",file)); return (await apiClient.post("/candidates/bulk-upload/",data)).data; }
export async function updateCandidate(id: number, payload: Record<string, unknown>) { return (await apiClient.patch(`/candidates/${id}/`,payload)).data; }
export async function deleteCandidate(id: number) { return (await apiClient.delete(`/candidates/${id}/`)).data; }
export async function analyzeCandidate(id: number) { return (await apiClient.post(`/candidates/${id}/analyze/`)).data; }
export async function runMatch(candidateId: number,jobId: number) { return (await apiClient.post("/match/",{candidate_id:candidateId,job_id:jobId})).data; }
