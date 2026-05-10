export type ContrastLevel = 'low' | 'normal' | 'high' | 'max';
export type Density = 'compact' | 'default' | 'comfortable';
export type Theme = 'light' | 'dark';

export interface UIState {
  font_scale: number;
  contrast_level: ContrastLevel;
  density: Density;
  theme: Theme;
  hit_target_min_px: number;
  reduced_motion: boolean;
  hide_nonessential: boolean;
}

export interface UserProfile {
  assistive_tech: boolean;
  visual_pref: number;
  motor_pref: number;
  cognitive_pref: number;
  reduced_motion_preferred?: boolean;
  vulnerable?: boolean;
}

export interface SessionBehavior {
  click_latency_ms: number;
  error_count: number;
  scroll_depth: number;
  task_stage: number;
  total_steps: number;
}

export interface A11yDiagnostics {
  risk_score: number;
}

export interface ContextFeatures {
  user_profile: UserProfile;
  session_behavior: SessionBehavior;
  ui_state: UIState;
  a11y_diagnostics: A11yDiagnostics;
}

export interface DecideResponse {
  decision_id: string;
  context_id: string;
  action_id: string;
  action_label: string;
  action_payload: Record<string, unknown>;
  confidence: number;
  arm_scores: Record<string, number>;
  model_version: number;
  requires_hitl: boolean;
  hitl_trigger: string | null;
  validation: ValidationSummary;
}

export interface Violation {
  rule_id: string;
  rule_name: string;
  severity: 'info' | 'warn' | 'fail';
  message: string;
  sc_reference: string;
}

export interface ValidationSummary {
  status: 'pass' | 'warn' | 'fail';
  violations: Violation[];
  simulated_state: Partial<UIState>;
  hard_failures: number;
  warnings: number;
}

export interface ExecuteResponse {
  execution_id: string;
  decision_id: string;
  applied_action_id: string;
  applied_ui_state: Partial<UIState>;
  was_blocked: boolean;
  was_fallback: boolean;
  block_reason: string | null;
}

export interface HitlReviewItem {
  review_id: string;
  decision_id: string;
  context_id: string;
  candidate_action_id: string;
  candidate_action_label: string;
  candidate_payload: Record<string, unknown>;
  trigger_reason: string;
  confidence: number;
  validation_summary: ValidationSummary;
  user_id: string;
  session_id: string;
  created_at: string;
}

export interface MetricsResponse {
  total_decisions: number;
  total_executions: number;
  total_blocked: number;
  total_fallbacks: number;
  compliance_rate: number;
  pending_hitl: number;
  resolved_hitl: number;
  approval_rate: number;
  avg_reward: number;
  avg_confidence: number;
  model_version: number;
  arm_pulls: Record<string, number>;
  arm_avg_reward: Record<string, number>;
}

export interface ActionInfo {
  id: string;
  label: string;
  description: string;
  payload: Record<string, unknown>;
}

// ─── axe-core types ──────────────────────────────────────────────────────────

export type AxeImpact = 'minor' | 'moderate' | 'serious' | 'critical';

export interface AxeViolation {
  id: string;
  impact: AxeImpact;
  description: string;
  help: string;
  helpUrl: string;
  sc_references: string[];
  node_count: number;
}

export interface AxeResult {
  /** null while scan is in flight */
  scanned_at: string | null;
  violations: AxeViolation[];
  passes: number;
  incomplete: number;
  source: 'axe-core';
}
