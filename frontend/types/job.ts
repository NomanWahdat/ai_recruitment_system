export type Job = {
  id: number;
  title: string;
  company_name: string;
  location?: string;
  employment_type?: string;
  description?: string;
  required_skills?: string[];
  minimum_experience?: number;
  education_requirement?: string;
  salary_range?: string;
};
