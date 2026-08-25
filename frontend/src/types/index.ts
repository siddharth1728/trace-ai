/**
 * TypeScript Data Transfer Models matching TRACE v0.3 REST API.
 */

export type SessionStatus = 'CREATED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';

export type HypothesisStatus =
  | 'PROPOSED'
  | 'SUPPORTED'
  | 'WEAKENED'
  | 'REJECTED'
  | 'VERIFICATION_PENDING'
  | 'VERIFIED'
  | 'DISPROVEN'
  | 'CONFIRMED';

export interface PlanStep {
  id: string;
  step_index: number;
  title: string;
  tool_name: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'DONE' | 'SKIPPED' | 'FAILED';
  expected_outcome: string;
  observation_id?: string | null;
}

export interface Observation {
  id: string;
  step_index: number;
  tool_name: string;
  summary: string;
  is_success: boolean;
  input_args: Record<string, any>;
  output_data: Record<string, any>;
  evidence_tags: string[];
  created_at: string;
}

export interface Evidence {
  id: string;
  observation_id?: string | null;
  target_hypothesis_id?: string | null;
  evidence_type: 'DIRECT' | 'DERIVED';
  relation: 'SUPPORTS' | 'CONTRADICTS' | 'DERIVED_FROM' | 'VERIFIES' | 'DISPROVES';
  statement: string;
  confidence_weight: number;
  created_at: string;
}

export interface Hypothesis {
  id: string;
  statement: string;
  status: HypothesisStatus;
  confidence: number;
  rationale: string;
  supporting_evidence_ids: string[];
  counterexample_ids: string[];
}

export interface Countercheck {
  id: string;
  hypothesis_id: string;
  strategy: string;
  description: string;
  harness_code: string;
  executed: boolean;
  passed: boolean;
  disproved: boolean;
  actual_output: string;
}

export interface FinalDiagnosis {
  problem_statement?: string | null;
  likely_root_cause?: string | null;
  learning_point?: string | null;
  suggested_fix_guidance?: string | null;
  confidence: number;
  verified_hypothesis_id?: string | null;
  countercheck_summary?: string | null;
  what_trace_checked: string[];
  what_remains_uncertain: string[];
  evidence_summary: string[];
}

export interface SessionDetail {
  id: string;
  title: string;
  user_goal: string;
  source_code: string;
  file_path?: string | null;
  error_description?: string | null;
  traceback_input?: string | null;
  status: SessionStatus;
  confidence: number;
  created_at: string;
  updated_at: string;
  diagnosis?: FinalDiagnosis | null;
  plan_steps: PlanStep[];
  observations: Observation[];
  evidence: Evidence[];
  hypotheses: Hypothesis[];
  counterchecks: Countercheck[];
}

export interface SessionSummary {
  id: string;
  title: string;
  user_goal: string;
  status: SessionStatus;
  confidence: number;
  likely_root_cause?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  total: number;
}

export interface CreateSessionPayload {
  user_goal: string;
  source_code: string;
  title?: string;
  error_description?: string;
  traceback_input?: string;
}

export interface InvestigatePayload {
  provider?: string;
  max_iterations?: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  product: string;
}

export interface FeatureContribution {
  feature_name: string;
  feature_value: number;
  contribution_weight: number;
  description: string;
}

export interface BehaviorPrediction {
  session_id: string;
  predicted_archetype: 'SYSTEMATIC_VERIFICATION' | 'RAPID_TRIAL_AND_ERROR' | 'UNFOCUSED_EXPLORATION';
  confidence: number;
  top_contributing_factors: FeatureContribution[];
  pedagogical_explanation: string;
  model_type: string;
  model_version: string;
  created_at: string;
}

export interface DeterministicHabitStats {
  total_sessions: number;
  ast_first_rate: number;
  traceback_provided_rate: number;
  countercheck_rigor_rate: number;
  avg_investigation_steps: number;
  avg_hypotheses_per_session: number;
  tool_failure_rate: number;
}

export interface StudentProfile {
  deterministic_habits: DeterministicHabitStats;
  latest_prediction?: BehaviorPrediction | null;
  archetype_history: Record<string, number>;
  key_strengths: string[];
  growth_areas: string[];
  updated_at: string;
}
