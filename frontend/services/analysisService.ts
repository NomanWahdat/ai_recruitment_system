import { apiClient } from "@/lib/axios";
import type { Analysis, Page, ScoreRun, ScoreVerification, EvaluationReport } from "@/types/domain";
export async function getAnalyses(params: Record<string, number> = {}): Promise<Analysis[]> {
  return (await apiClient.get<Page<Analysis>>("/analyses/", {params})).data.results;
}

export async function getScoreRuns(analysis: number, page: number): Promise<Page<ScoreRun>> {
  return (await apiClient.get("/score-runs/", {params: {analysis, page}})).data;
}
export async function verifyScore(analysis: number, run?: number): Promise<ScoreVerification> {
  return (await apiClient.get(run ? `/score-runs/${run}/reproduce/` : `/analyses/${analysis}/reproduce/`)).data;
}
export async function getEvaluation(): Promise<EvaluationReport> {
  return (await apiClient.get("/evaluation/")).data;
}
