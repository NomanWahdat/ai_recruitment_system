import { apiClient } from "@/lib/axios";
import type { Job, Page } from "@/types/domain";
export async function listJobs(params: Record<string, string | number> = {}): Promise<Page<Job>> { return (await apiClient.get("/jobs/", {params})).data; }
export async function getJobs() { return (await listJobs()).results; }
export async function getJobById(id: number): Promise<Job> { return (await apiClient.get(`/jobs/${id}/`)).data; }
export async function createJob(payload: Record<string, unknown>) { return (await apiClient.post("/jobs/", payload)).data; }
export async function updateJob(id: number, payload: Record<string, unknown>) { return (await apiClient.patch(`/jobs/${id}/`, payload)).data; }
export async function deleteJob(id: number) { return (await apiClient.delete(`/jobs/${id}/`)).data; }
export async function getJobRankings(id: number) { return (await apiClient.get(`/jobs/${id}/rankings/`)).data; }
export async function runMatchingEngine(id: number) { return (await apiClient.post(`/jobs/${id}/match/`)).data; }
