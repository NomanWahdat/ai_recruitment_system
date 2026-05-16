export type Analysis = {
  id: number;
  job: number;
  candidate: number;
  match_score: number;
  matched_skills: string[];
  missing_skills: string[];
  strengths?: string;
  weaknesses?: string;
  ai_summary?: string;
  recommendation_status?: string;
  generated_interview_questions?: string[];
  ranking_position?: number | null;
};
