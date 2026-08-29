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

export type InvestigationMode = 'GUIDED' | 'INTERACTIVE';

export interface StudentHypothesis {
  id: string;
  turn_number: number;
  hypothesis_text: string;
  target_function_or_line?: string | null;
  student_confidence?: number | null;
  status: 'UNTESTED' | 'SUPPORTED' | 'CONTRADICTED' | 'REVISED' | 'ABANDONED';
  evaluation_observation_id?: string | null;
  created_at: string;
}

export interface CodeRevision {
  id: string;
  revision_number: number;
  source_code: string;
  intent_notes?: string | null;
  time_since_previous_sec: number;
  lines_added: number;
  lines_deleted: number;
  lines_modified: number;
  total_loc: number;
  cyclomatic_complexity_delta: number;
  modified_ast_nodes: string[];
  modified_functions: string[];
  execution_success: boolean;
  runtime_error_type?: string | null;
  resolved_error: boolean;
  created_at: string;
}

export interface StudentTestInput {
  id: string;
  turn_number: number;
  input_expression: string;
  student_rationale?: string | null;
  is_boundary_case: boolean;
  executed: boolean;
  execution_success: boolean;
  stdout: string;
  stderr: string;
  exception_type?: string | null;
  execution_time_ms: number;
  created_at: string;
}

export interface SocraticPrompt {
  id: string;
  question_text: string;
  focus_area: string;
  target_code_snippet?: string | null;
  suggested_options: string[];
  turn_number: number;
  answered: boolean;
  student_response?: string | null;
  skipped: boolean;
}

export interface InteractionTurn {
  id: string;
  turn_number: number;
  speaker: 'STUDENT' | 'TRACE';
  action_type: string;
  content_text: string;
  referenced_entity_id?: string | null;
  created_at: string;
}

export interface StudentActivitySummary {
  revisions_count: number;
  hypotheses_count: number;
  custom_tests_count: number;
  boundary_tests_count: number;
  socratic_questions_answered: number;
  total_turns: number;
}

export interface SessionDetail {
  id: string;
  title: string;
  user_goal: string;
  source_code: string;
  file_path?: string | null;
  error_description?: string | null;
  traceback_input?: string | null;
  mode: InvestigationMode;
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
  student_hypotheses: StudentHypothesis[];
  revisions: CodeRevision[];
  student_test_inputs: StudentTestInput[];
  interaction_turns: InteractionTurn[];
  active_socratic_prompt?: SocraticPrompt | null;
  student_activity?: StudentActivitySummary | null;
}

export interface SessionSummary {
  id: string;
  title: string;
  user_goal: string;
  mode?: InvestigationMode;
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
  mode?: InvestigationMode;
}

export interface CreateStudentHypothesisPayload {
  hypothesis_text: string;
  target_function_or_line?: string;
  student_confidence?: number;
}

export interface CreateCodeRevisionPayload {
  source_code: string;
  intent_notes?: string;
  time_since_previous_sec?: number;
}

export interface CreateStudentTestInputPayload {
  input_expression: string;
  student_rationale?: string;
  is_boundary_case?: boolean;
}

export interface AnswerSocraticPayload {
  prompt_id: string;
  student_response?: string;
  skip?: boolean;
}

export interface StudentTestExecutionResult {
  test_id: string;
  executed: boolean;
  execution_success: boolean;
  stdout: string;
  stderr: string;
  exception_type?: string | null;
  execution_time_ms: number;
  supports_student_hypothesis?: boolean | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  product: string;
}

export interface InvestigatePayload {
  provider?: string;
  max_iterations?: number;
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
  key_strengths: string[];
  growth_areas: string[];
  updated_at: string;
}
