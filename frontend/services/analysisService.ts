import { apiClient } from "@/lib/axios";

export async function getAnalyses() {
  const response = await apiClient.get("/analyses/");
  return response.data;
}
