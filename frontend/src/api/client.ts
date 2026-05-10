import type {
  DecideResponse,
  ExecuteResponse,
  HitlReviewItem,
  MetricsResponse,
  ActionInfo,
  ContextFeatures,
  UIState,
  ValidationSummary,
} from '../types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} -> ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  postContext(payload: {
    user_id: string;
    session_id: string;
    context_features: ContextFeatures;
    ui_state: UIState;
  }) {
    return request<{ context_id: string }>('/api/context', {
      method: 'POST',
      body: JSON.stringify({
        ...payload,
        timestamp: new Date().toISOString(),
      }),
    });
  },
  decide(context_id: string) {
    return request<DecideResponse>('/api/adapt/decide', {
      method: 'POST',
      body: JSON.stringify({ context_id }),
    });
  },
  validate(context_id: string, action_id: string) {
    return request<ValidationSummary>('/api/adapt/validate', {
      method: 'POST',
      body: JSON.stringify({ context_id, action_id }),
    });
  },
  execute(decision_id: string) {
    return request<ExecuteResponse>('/api/adapt/execute', {
      method: 'POST',
      body: JSON.stringify({ decision_id }),
    });
  },
  updatePolicy(payload: {
    decision_id: string;
    task_completed: boolean;
    completion_time_ms: number;
    time_budget_ms: number;
    error_count: number;
    error_budget: number;
    trust_score: number;
  }) {
    return request<{ update_id: string; model_version: number; final_reward: number }>(
      '/api/policy/update',
      { method: 'POST', body: JSON.stringify(payload) }
    );
  },
  hitlQueue() {
    return request<HitlReviewItem[]>('/api/hitl/queue');
  },
  submitReview(payload: {
    decision_id: string;
    decision: 'approve' | 'reject' | 'override';
    reviewer_id: string;
    reviewer_role: 'accessibility_reviewer' | 'product_owner' | 'system';
    reason?: string;
  }) {
    return request<{ ok: boolean; decision: string }>('/api/hitl/review', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  metrics() {
    return request<MetricsResponse>('/api/metrics');
  },
  actions() {
    return request<ActionInfo[]>('/api/actions');
  },

  reportAxeViolations(payload: {
    decision_id: string;
    violations: Array<{
      id: string;
      impact: string;
      description: string;
      help: string;
      sc_references: string[];
      node_count: number;
    }>;
    passes: number;
    incomplete: number;
    scanned_at: string;
  }) {
    return request<{ ok: boolean }>('/api/adapt/axe-report', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
