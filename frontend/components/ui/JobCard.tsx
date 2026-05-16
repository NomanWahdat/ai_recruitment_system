import Link from "next/link";
import type { ReactNode } from "react";

type JobCardProps = {
  id?: number;
  title?: string;
  companyName?: string;
  location?: string;
  experience?: number;
  skills?: string[];
  href?: string;
  actions?: ReactNode;
};

export function JobCard({
  title = "Backend Django Developer",
  companyName = "Company",
  location = "Remote",
  experience = 3,
  skills = ["Python", "Django", "PostgreSQL"],
  href,
  actions,
}: JobCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="text-lg font-semibold text-slate-900">{href ? <Link href={href}>{title}</Link> : title}</div>
      <div className="mt-1 text-sm font-medium text-slate-500">{companyName}</div>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        Placeholder job card with title, company, experience, and skill summary for future integration.
      </p>
      <div className="mt-4 text-sm text-slate-600">{location} • {experience}+ years</div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-blue-700">
        {skills.map((skill) => (
          <span key={skill} className="rounded-full bg-blue-50 px-3 py-1 font-medium">{skill}</span>
        ))}
      </div>
      {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
    </article>
  );
}
