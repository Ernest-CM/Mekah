import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { applyUIState, DEFAULT_UI_STATE, mergeAdaptation } from '../theme/theme';
import type {
  ContextFeatures,
  DecideResponse,
  ExecuteResponse,
  UIState,
  UserProfile,
  SessionBehavior,
} from '../types';

interface AdaptArgs {
  user_id: string;
  session_id: string;
  user_profile: UserProfile;
  behavior: SessionBehavior;
  riskScore?: number;
}

export interface AdaptationLogEntry {
  decision: DecideResponse;
  execution: ExecuteResponse | null;
  pending: boolean;
  ts: string;
}

export function useAdaptiveUI(initial: UIState = DEFAULT_UI_STATE) {
  const [uiState, setUiState] = useState<UIState>(initial);
  const [log, setLog] = useState<AdaptationLogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const lastDecisionRef = useRef<DecideResponse | null>(null);

  useEffect(() => {
    applyUIState(uiState);
  }, [uiState]);

  const setUi = useCallback((next: UIState | ((prev: UIState) => UIState)) => {
    setUiState((prev) => {
      const v = typeof next === 'function' ? (next as (p: UIState) => UIState)(prev) : next;
      return v;
    });
  }, []);

  const requestAdaptation = useCallback(
    async (args: AdaptArgs): Promise<DecideResponse | null> => {
      setBusy(true);
      try {
        const features: ContextFeatures = {
          user_profile: args.user_profile,
          session_behavior: args.behavior,
          ui_state: uiState,
          a11y_diagnostics: { risk_score: args.riskScore ?? 0 },
        };
        const ctx = await api.postContext({
          user_id: args.user_id,
          session_id: args.session_id,
          context_features: features,
          ui_state: uiState,
        });
        const decision = await api.decide(ctx.context_id);
        lastDecisionRef.current = decision;

        if (decision.requires_hitl) {
          setLog((l) => [
            { decision, execution: null, pending: true, ts: new Date().toISOString() },
            ...l,
          ]);
          return decision;
        }

        const exec = await api.execute(decision.decision_id);
        setUiState((prev) => mergeAdaptation(prev, exec.applied_ui_state));
        setLog((l) => [
          { decision, execution: exec, pending: false, ts: new Date().toISOString() },
          ...l,
        ]);
        return decision;
      } finally {
        setBusy(false);
      }
    },
    [uiState]
  );

  const finalizePending = useCallback(async (decisionId: string) => {
    const exec = await api.execute(decisionId);
    setUiState((prev) => mergeAdaptation(prev, exec.applied_ui_state));
    setLog((l) =>
      l.map((e) =>
        e.decision.decision_id === decisionId
          ? { ...e, execution: exec, pending: false }
          : e
      )
    );
    return exec;
  }, []);

  const reportOutcome = useCallback(
    async (
      decision_id: string,
      outcome: {
        task_completed: boolean;
        completion_time_ms: number;
        time_budget_ms: number;
        error_count: number;
        error_budget: number;
        trust_score: number;
      }
    ) => {
      return api.updatePolicy({ decision_id, ...outcome });
    },
    []
  );

  return {
    uiState,
    setUi,
    log,
    busy,
    requestAdaptation,
    finalizePending,
    reportOutcome,
    lastDecision: lastDecisionRef,
  };
}
