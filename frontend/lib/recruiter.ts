export const stageLabels: Record<string, string> = {applied: "New application", review: "In review", shortlisted: "Shortlisted", interview: "Interview", hired: "Hired", rejected: "Not selected"};
export const processingLabels: Record<string, string> = {pending: "Waiting to be read", processing: "Reading resume", completed: "Ready to check", failed: "Needs attention"};
export function readableEmail(value: string) {return value.endsWith("@example.invalid") ? "Email not found yet" : value || "Email not provided";}
