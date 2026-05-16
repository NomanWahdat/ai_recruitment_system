import Link from "next/link";
import { SkillBadge } from "./SkillBadge";
import { ScoreBar } from "./ScoreBar";
import type { ReactNode } from "react";

type CandidateCardProps = {
  id?: number;
  fullName?: string;
  email?: string;
  skills?: string[];
  yearsOfExperience?: number;
  analysisCompleted?: boolean;
  matchScore?: number;
  href?: string;
  actions?: ReactNode;
};

export function CandidateCard({
  id,
  fullName = "Candidate Name",
  email = "candidate@email.com",
  skills = ["Python", "Django", "PostgreSQL"],
  yearsOfExperience = 4,
  analysisCompleted = true,
  matchScore = 78,
  href,
  actions,
}: CandidateCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-semibold text-slate-900">
            {href ? <Link href={href}>{fullName}</Link> : fullName}
          </div>
          <div className="text-sm text-slate-500">{email}</div>
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
          {analysisCompleted ? "Analyzed" : "Pending"}
        </span>
      </div>
      <div className="mt-4">
        <div className="mb-2 text-xs text-slate-500">Experience: {yearsOfExperience} years</div>
        <ScoreBar value={matchScore} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {skills.map((skill) => (
          <SkillBadge key={skill} label={skill} />
        ))}
      </div>
      {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
    </article>
  );
}
