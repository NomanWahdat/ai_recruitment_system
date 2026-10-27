"use client";

export function ResponseSourceBadge({ source, model, reason }: {
  source: string | undefined | null;
  model?: string;
  reason?: string;
}) {
  if (!source) return null;
  const label = source === "groq" ? "Groq AI" : source === "gemini" ? "Gemini AI" : "Local rubric";
  return <div className="space-y-2">
    <span className="inline-block rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
      {label}{model ? ` / ${model}` : ""}
    </span>
    {source === "local" && <p className="text-xs leading-5 text-amber-800">
      {reason || "Generated using local rules. This is not an AI response."}
    </p>}
  </div>;
}
