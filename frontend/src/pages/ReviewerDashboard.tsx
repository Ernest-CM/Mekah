import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import ValidationPanel from '../components/ValidationPanel';
import type { HitlReviewItem } from '../types';

type Role = 'accessibility_reviewer' | 'product_owner';

const TRIGGER_LABELS: Record<string, string> = {
  validator_warn: 'Validator warning',
  low_confidence: 'Low policy confidence',
  high_impact_region: 'High-impact UI region',
  vulnerable_profile: 'Vulnerable user profile',
};

export default function ReviewerDashboard() {
  const [queue, setQueue] = useState<HitlReviewItem[]>([]);
  const [reviewerId, setReviewerId] = useState('reviewer-1');
  const [role, setRole] = useState<Role>('accessibility_reviewer');
  const [reasonByDecision, setReasonByDecision] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const items = await api.hitlQueue();
      setQueue(items);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  async function decide(item: HitlReviewItem, decision: 'approve' | 'reject' | 'override') {
    setBusy(item.decision_id);
    try {
      await api.submitReview({
        decision_id: item.decision_id,
        decision,
        reviewer_id: reviewerId,
        reviewer_role: role,
        reason: reasonByDecision[item.decision_id],
      });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  const overrideAllowed = role === 'product_owner';

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div className="card stack">
        <h2 style={{ margin: 0 }}>HITL governance</h2>
        <p className="muted" style={{ margin: 0 }}>
          Reviewer queue per <code>revised.md §8</code>. Approve or reject pending
          adaptations. Overrides require <strong>product_owner</strong> role and a written
          reason; they bypass safety blocks but are flagged for audit.
        </p>
        <div className="row">
          <label className="stack" style={{ gap: 4 }}>
            Reviewer ID
            <input
              value={reviewerId}
              onChange={(e) => setReviewerId(e.target.value)}
              style={{ minWidth: 200 }}
            />
          </label>
          <label className="stack" style={{ gap: 4 }}>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="accessibility_reviewer">Accessibility reviewer</option>
              <option value="product_owner">Product owner</option>
            </select>
          </label>
          <button onClick={refresh}>Refresh queue</button>
        </div>
        {error && <p className="tag fail">{error}</p>}
      </div>

      {queue.length === 0 ? (
        <div className="card">
          <p className="muted" style={{ margin: 0 }}>
            No pending reviews. New flagged adaptations will show up here automatically.
          </p>
        </div>
      ) : (
        queue.map((item) => (
          <div key={item.review_id} className="card stack" style={{ borderColor: 'var(--warn)' }}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h3 style={{ margin: 0 }}>
                Decision <code>{item.decision_id.slice(0, 8)}…</code>
              </h3>
              <span className="tag warn">
                {TRIGGER_LABELS[item.trigger_reason] ?? item.trigger_reason}
              </span>
            </div>
            <div className="row">
              <span className="tag">User: {item.user_id}</span>
              <span className="tag">Session: {item.session_id}</span>
              <span className="tag">Confidence: {item.confidence.toFixed(2)}</span>
            </div>

            <div className="card" style={{ background: 'var(--bg)' }}>
              <strong>Proposed action:</strong> <code>{item.candidate_action_id}</code>{' '}
              {item.candidate_action_label}
              <div className="muted" style={{ marginTop: 6, fontSize: '0.92em' }}>
                payload: <code>{JSON.stringify(item.candidate_payload)}</code>
              </div>
            </div>

            <ValidationPanel summary={item.validation_summary} />

            <label className="stack" style={{ gap: 4 }}>
              Reason (required for overrides)
              <textarea
                rows={2}
                value={reasonByDecision[item.decision_id] ?? ''}
                onChange={(e) =>
                  setReasonByDecision((m) => ({ ...m, [item.decision_id]: e.target.value }))
                }
                placeholder="Why are you approving / rejecting / overriding?"
              />
            </label>

            <div className="row">
              <button
                className="primary"
                disabled={busy === item.decision_id}
                onClick={() => decide(item, 'approve')}
              >
                Approve
              </button>
              <button
                className="danger"
                disabled={busy === item.decision_id}
                onClick={() => decide(item, 'reject')}
              >
                Reject
              </button>
              <button
                disabled={busy === item.decision_id || !overrideAllowed}
                onClick={() => decide(item, 'override')}
                title={
                  overrideAllowed
                    ? 'Override safety constraints (audited)'
                    : 'Override requires Product Owner role'
                }
              >
                Override
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
