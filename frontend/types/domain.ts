export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }
export interface Job { employment_type:string; salary_range:string; id: number; title: string; company_name: string; description: string; required_skills: string[]; minimum_experience: number; education_requirement: string; location: string; scoring_weights: Record<string, number>; revision: number }
export interface Candidate { id: number; full_name: string; email: string; phone_number: string; years_of_experience: string; skills: string[]; education: string; processing_status: string; extraction_error: string; analysis_error: string; extracted_text: string; analysis_completed: boolean; profile_reviewed_at: string | null; evidence: Record<string, {line: number; text: string}[]>; cv_download_url: string | null; retention_until: string | null }
export interface Decision { id:number; reviewer:number|null; from_stage:string; to_stage:string; note:string; created_at:string }
export interface Application { decisions: Decision[]; id: number; candidate: number; job: number; candidate_name: string; job_title: string; stage: string; review_note: string }
export interface Task { id: number; kind: string; status: string; candidate: number | null; job: number | null; attempts: number; error: string; created_at: string }
export interface AuditEvent { id: number; action: string; target_type: string; target_id: string; created_at: string; details: Record<string, string> }
export interface Dashboard { candidates: number; jobs: number; scores: {total: number; average: number | null; high: number; medium: number; low: number}; queued: number; failed: number; worker_online: boolean; events: AuditEvent[] }
export interface Analysis { job_title?: string; generated_interview_questions?: string[]; scoring_snapshot: ScoringSnapshot | Record<string, never>; insufficient_requirements:boolean; id: number; job: number; candidate: number; candidate_name: string; match_score: number; is_stale: boolean; provider: string; provider_model?: string; generation_provenance?: Record<string, {fallback_reason?: string; provider?: string; model?: string}>; scoring_version: string; score_components: Record<string,{ratio: number | null; weight: number}>; matched_skills: string[]; missing_skills: string[]; ai_summary: string }

export interface ScoringSnapshot {
  schema_version: string;
  sha256: string;
  calculated_at: string;
  final_score: number;
  insufficient_requirements: boolean;
  formula: string;
  inputs: {candidate: {skills: string[]; years: number; education: string; revision: number | null}; job: {required_skills: string[]; minimum_experience: number; education_requirement: string; scoring_weights: Record<string, number>; revision: number | null}};
  rubric: {version: string; score: number; components: Record<string, {ratio: number | null; weight: number}>; matched_skills: string[]; missing_skills: string[]};
  ai: {enabled: boolean; provider: string; model: string; score: number | null; requested_weight: number; applied_weight: number; prompt_version: string; fallback_reason: string};
}
export interface ScoreRun {id: number; analysis: number; created_at: string; snapshot: ScoringSnapshot}
export interface ScoreVerification {available: boolean; verified: boolean; reason: string; reproduced_score?: number; saved_score?: number; hash_matches?: boolean; external_requests?: number}
export interface EvaluationMetrics {email_accuracy: number; skill_precision: number; skill_recall: number; skill_f1: number; experience_mae_years: number}
export interface RankingMetrics {ndcg_at_k: number; recall_at_k: number | null; mrr: number; ordered_ids: string[]; scores: number[]}
export interface EvaluationCase {id: string; split: string; category: string; email_correct: boolean; experience_absolute_error: number; unexpected_skills: string[]; missing_skills: string[]}
export interface EvaluationGroup extends EvaluationMetrics {records: number; ranking: Record<string, Record<string, RankingMetrics>>}
export interface EvaluationReport extends EvaluationGroup {dataset_version: string; dataset_sha256: string; implementation_sha256: string; as_of_date: string; mode: string; k: number; confidence_intervals_95: Record<string, [number, number]>; by_split: Record<string, EvaluationGroup>; failure_cases: EvaluationCase[]; limitations: string[]; external_requests: number; cross_split_duplicate_documents: number; independent_human_agreement: {quadratic_weighted_kappa: number | null; rated_pairs: number} | null; checks: {passed: boolean; split: string; scope: string}}
