import type { EvaluationReport } from "@/types/domain";
import { evaluationSummaryHtml } from "./evaluationSummary";
export function downloadJson(filename: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadEvaluationSummary(report: EvaluationReport) {
  const url = URL.createObjectURL(new Blob([evaluationSummaryHtml(report)], {type: "text/html;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = "recruitment-software-test-summary.html";
  link.click();
  URL.revokeObjectURL(url);
}
