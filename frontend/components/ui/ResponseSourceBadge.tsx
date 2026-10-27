"use client";
export function ResponseSourceBadge({source, model, reason}: {source: string | undefined | null; model?: string; reason?: string}) {
  if (!source) return null;
  const ai = source === "groq" || source === "gemini";
  return <div className="space-y-2 text-xs"><span className={`inline-block rounded-full px-3 py-1 font-medium ${ai ? "bg-blue-50 text-blue-800" : "bg-slate-100 text-slate-700"}`}>{ai ? "AI-assisted" : "Standard matching"}</span>{!ai && <p className="max-w-2xl leading-5 text-slate-600">This result uses the built-in comparison rules. AI was not used.</p>}<details className="text-slate-500"><summary className="cursor-pointer">Source details</summary><p className="mt-2">Provider: {source}{model ? ` / Model: ${model}` : ""}.</p>{reason && <p className="mt-1 max-w-2xl leading-5">{reason}</p>}</details></div>;
}
