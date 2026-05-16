"use client";

interface ResponseSourceBadgeProps {
  source: string | undefined | null;
}

export function ResponseSourceBadge({ source }: ResponseSourceBadgeProps) {
  if (!source) return null;

  const isAI = source === "groq_ai";
  const label = isAI ? "Groq AI Response" : "Local Response";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
        isAI
          ? "bg-green-50 text-green-700 ring-1 ring-green-200"
          : "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${isAI ? "bg-green-500" : "bg-amber-500"}`}
      />
      {label}
    </span>
  );
}
