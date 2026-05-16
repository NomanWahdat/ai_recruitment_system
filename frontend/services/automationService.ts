import { apiClient } from "@/lib/axios";

export async function reprocessAutomation() {
  const response = await apiClient.post("/automation/reprocess/");
  return response.data;
}

export async function rerunMatchingEngine() {
  const response = await apiClient.post("/automation/matching/");
  return response.data;
}
