import { useEffect, useMemo, useState } from 'react';
import AxePanel from '../components/AxePanel';
import ProfilePicker, { PROFILE_PRESETS } from '../components/ProfilePicker';
import ValidationPanel from '../components/ValidationPanel';
import { api } from '../api/client';
import { useAdaptiveUI } from '../hooks/useAdaptiveUI';
import { useAxeValidation } from '../hooks/useAxeValidation';
import { useTelemetry } from '../hooks/useTelemetry';
import { DEFAULT_UI_STATE } from '../theme/theme';
import type { DecideResponse, UserProfile } from '../types';

const TASK_STEPS = [
  {
    id: 1,
    prompt: 'Find your account dashboard.',
    options: ['Settings', 'Dashboard', 'Reports', 'Help'],
    answer: 'Dashboard',
  },
  {
    id: 2,
    prompt: 'Locate the action labelled "Update profile".',
    options: ['Update profile', 'Manage payments', 'Sign out', 'Reset password'],
    answer: 'Update profile',
  },
  {
    id: 3,
    prompt: 'Submit the form to save your changes.',
    options: ['Cancel', 'Discard', 'Submit', 'Reload'],
    answer: 'Submit',
  },
  {
    id: 4,
    prompt: 'Confirm the success message has appeared.',
    options: ['Close', 'Confirm received', 'Re-open', 'Print'],
    answer: 'Confirm received',
  },
];

const TIME_BUDGET_MS = 60_000;
const ERROR_BUDGET = 4;

function newSessionId() {
  return `sess_${Math.random().toString(36).slice(2, 10)}`;
}

export default function DemoTask() {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [profileId, setProfileId] = useState('default');
  const [stepIdx, setStepIdx] = useState(0);
  const [pendingDecision, setPendingDecision] = useState<DecideResponse | null>(null);
  const [trustScore, setTrustScore] = useState(0.7);
  const [taskStartedAt, setTaskStartedAt] = useState<number>(performance.now());
  const [outcomeReported, setOutcomeReported] = useState(false);

  const profile: UserProfile = useMemo(
    () => PROFILE_PRESETS.find((p) => p.id === profileId) ?? PROFILE_PRESETS[0],
    [profileId]
  );

  const { uiState, log, busy, requestAdaptation, finalizePending, reportOutcome } =
    useAdaptiveUI(DEFAULT_UI_STATE);
  const { behavior, recordClick, recordError, advanceStage, reset: resetTelemetry } =
    useTelemetry(TASK_STEPS.length);
  const { result: axeResult, scanning: axeScanning, scan: runAxeScan } = useAxeValidation();

  const completed = stepIdx >= TASK_STEPS.length;
  const currentStep = TASK_STEPS[Math.min(stepIdx, TASK_STEPS.length - 1)];

  useEffect(() => {
    if (pendingDecision) {
      const t = setInterval(async () => {
        try {
          const res = await fetch(`/api/hitl/queue`);
          if (!res.ok) return;
          const queue = await res.json();
          const stillOpen = queue.find(
            (q: { decision_id: string }) => q.decision_id === pendingDecision.decision_id
          );
          if (!stillOpen) {
            await finalizePending(pendingDecision.decision_id);
            setPendingDecision(null);
          }
        } catch (_e) {
          /* swallow */
        }
      }, 2000);
      return () => clearInterval(t);
    }
  }, [pendingDecision, finalizePending]);

  // Run axe scan after each executed adaptation and report violations to the backend.
  useEffect(() => {
    const latest = log[0];
    if (!latest || latest.pending || !latest.execution) return;

    const decisionId = latest.decision.decision_id;
    runAxeScan();

    // Report after debounce settles (hook uses 300ms internally).
    const timer = setTimeout(async () => {
      try {
        const axeResult2 = await import('axe-core').then((m) =>
          m.default.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
            resultTypes: ['violations', 'passes', 'incomplete'],
          })
        );
        await api.reportAxeViolations({
          decision_id: decisionId,
          violations: axeResult2.violations.map((v) => ({
            id: v.id,
            impact: v.impact ?? 'minor',
            description: v.description,
            help: v.help,
            sc_references: v.tags
              .filter((t) => /^wcag\d+$/.test(t))
              .map((t) => `WCAG 2.1 SC ${t.replace('wcag', '').split('').join('.')}`),
            node_count: v.nodes.length,
          })),
          passes: axeResult2.passes.length,
          incomplete: axeResult2.incomplete.length,
          scanned_at: new Date().toISOString(),
        });
      } catch (_e) {
        /* non-fatal — backend logging is best-effort */
      }
    }, 400);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [log]);

  async function handleAnswer(option: string) {
    recordClick();
    if (option !== currentStep.answer) {
      recordError();
      return;
    }
    const newStage = stepIdx + 1;
    advanceStage();
    setStepIdx(newStage);

    const decision = await requestAdaptation({
      user_id: 'demo-user',
      session_id: sessionId,
      user_profile: profile,
      behavior: { ...behavior, task_stage: newStage },
      riskScore: behavior.error_count > 0 ? Math.min(1, behavior.error_count / 5) : 0,
    });
    if (decision?.requires_hitl) setPendingDecision(decision);
  }

  async function finishAndReport() {
    if (outcomeReported) return;
    const lastDecisionId = log[0]?.decision.decision_id;
    if (!lastDecisionId) return;
    const elapsed = performance.now() - taskStartedAt;
    await reportOutcome(lastDecisionId, {
      task_completed: true,
      completion_time_ms: elapsed,
      time_budget_ms: TIME_BUDGET_MS,
      error_count: behavior.error_count,
      error_budget: ERROR_BUDGET,
      trust_score: trustScore,
    });
    setOutcomeReported(true);
  }

  function restart() {
    setSessionId(newSessionId());
    setStepIdx(0);
    setPendingDecision(null);
    setTaskStartedAt(performance.now());
    setOutcomeReported(false);
    resetTelemetry();
  }

  const lastEntry = log[0];

  return (
    <div className="stack" style={{ gap: 24 }}>
      <ProfilePicker
        selectedId={profileId}
        onChange={(p) => {
          setProfileId(p.id);
          restart();
        }}
      />

      <div
        className="card stack"
        aria-labelledby="task-h"
        style={{ borderColor: 'var(--accent)' }}
      >
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h2 id="task-h" style={{ margin: 0 }}>Task ({stepIdx} / {TASK_STEPS.length})</h2>
          <span className="tag">Session {sessionId}</span>
        </div>

        {!completed ? (
          <>
            <p style={{ fontSize: '1.1em', margin: 0 }}>
              <strong>Step {stepIdx + 1}:</strong> {currentStep.prompt}
            </p>
            <div className="row">
              {currentStep.options.map((opt) => (
                <button
                  key={opt}
                  className={opt === currentStep.answer ? 'primary' : ''}
                  onClick={() => handleAnswer(opt)}
                  disabled={busy || !!pendingDecision}
                >
                  {opt}
                </button>
              ))}
            </div>
            {behavior.error_count > 0 && (
              <p className="tag warn" style={{ alignSelf: 'flex-start' }}>
                {behavior.error_count} mis-clicks recorded
              </p>
            )}
          </>
        ) : (
          <div className="stack">
            <p style={{ margin: 0 }}>
              <strong>Task complete.</strong> Send the outcome to the policy update
              service so the LinUCB model can learn from this episode.
            </p>
            <label className="stack" style={{ gap: 4 }}>
              Trust score (how acceptable were the adaptations?)
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={trustScore}
                onChange={(e) => setTrustScore(parseFloat(e.target.value))}
                disabled={outcomeReported}
              />
              <span className="muted">{trustScore.toFixed(2)} / 1.0</span>
            </label>
            <div className="row">
              <button
                className="primary"
                onClick={finishAndReport}
                disabled={outcomeReported}
              >
                {outcomeReported ? 'Outcome reported' : 'Submit outcome to policy'}
              </button>
              <button onClick={restart}>Restart task</button>
            </div>
          </div>
        )}

        {pendingDecision && (
          <div className="card" style={{ borderColor: 'var(--warn)' }}>
            <strong>Awaiting human review</strong> — proposed action{' '}
            <code>{pendingDecision.action_id}</code> ({pendingDecision.action_label}) was
            flagged: <em>{pendingDecision.hitl_trigger}</em>. Open the HITL reviewer
            tab to approve or reject.
          </div>
        )}
      </div>

      {lastEntry && (
        <div className="row" style={{ alignItems: 'flex-start', gap: 24 }}>
          <div className="card stack" style={{ flex: '1 1 280px' }}>
            <h3 style={{ margin: 0 }}>Latest decision</h3>
            <div className="row">
              <span className="tag">Action: <code>{lastEntry.decision.action_id}</code></span>
              <span className="tag">Confidence: {lastEntry.decision.confidence.toFixed(2)}</span>
              <span className="tag">Model v{lastEntry.decision.model_version}</span>
            </div>
            <div className="muted">
              {lastEntry.decision.action_label}
              {lastEntry.decision.hitl_trigger && ` (HITL: ${lastEntry.decision.hitl_trigger})`}
            </div>
            {lastEntry.execution && (
              <div className="row">
                <span className={`tag ${lastEntry.execution.was_blocked ? 'fail' : lastEntry.execution.was_fallback ? 'warn' : 'ok'}`}>
                  {lastEntry.execution.was_blocked
                    ? `Blocked: ${lastEntry.execution.block_reason}`
                    : lastEntry.execution.was_fallback
                    ? `Fallback: ${lastEntry.execution.block_reason}`
                    : 'Applied'}
                </span>
              </div>
            )}
          </div>

          <div style={{ flex: '1 1 280px' }}>
            <ValidationPanel summary={lastEntry.decision.validation} />
          </div>

          <div style={{ flex: '1 1 280px' }}>
            <AxePanel result={axeResult} scanning={axeScanning} />
          </div>
        </div>
      )}

      <div className="card stack nonessential">
        <h3 style={{ margin: 0 }}>Live UI state</h3>
        <pre style={{ margin: 0, fontSize: '0.85em', whiteSpace: 'pre-wrap' }}>
{JSON.stringify(uiState, null, 2)}
        </pre>
        <h3>Telemetry</h3>
        <pre style={{ margin: 0, fontSize: '0.85em', whiteSpace: 'pre-wrap' }}>
{JSON.stringify(behavior, null, 2)}
        </pre>
      </div>
    </div>
  );
}
