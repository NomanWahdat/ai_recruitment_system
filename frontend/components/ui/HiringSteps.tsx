import Link from "next/link";
const steps = ["Create a job", "Add resumes", "Check details", "Compare", "Decide"];
export function HiringSteps({current}: {current?: number}) {
  return <ol aria-label="Hiring steps" className="flex flex-wrap gap-x-5 gap-y-3 rounded-2xl border bg-white p-4 text-sm">{steps.map((label,index) => <li key={label} aria-current={current === index ? "step" : undefined} className={`flex items-center gap-2 ${current === index ? "font-semibold text-blue-800" : "text-slate-500"}`}><span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${current === index ? "bg-blue-600 text-white" : "bg-slate-100"}`}>{index + 1}</span>{label}</li>)}</ol>;
}
export function AdvancedPageLink() {return <Link href="/settings" className="inline-block text-sm font-medium text-blue-700 hover:underline">Back to Settings & tools</Link>;}
