import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ActionInfo, MetricsResponse } from '../types';

function pct(x: number) {
  return `${(x * 100).toFixed(1)}%`;
}

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [actions, setActions] = useState<ActionInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [m, a] = await Promise.all([api.metrics(), api.actions()]);
      setMetrics(m);
      setActions(a);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [refresh]);

  if (error) return <div className="card"><p className="tag fail">{error}</p></div>;
  if (!metrics) return <div className="card"><p className="muted">Loading metrics…</p></div>;

  const targetCompliance = 0.98;
  const meets = metrics.compliance_rate >= targetCompliance;

  return (
    <div className="stack" style={{ gap: 24 }}>
      <div className="card stack">
        <h2 style={{ margin: 0 }}>System metrics</h2>
        <p className="muted" style={{ margin: 0 }}>
          Live monitoring per <code>revised.md §5.1</code>. Target: WCAG compliance ≥ 98%, mean
          reward improvement ≥ 15%.
        </p>
        <div className="row" style={{ gap: 24 }}>
          <Stat label="Decisions" value={metrics.total_decisions.toString()} />
          <Stat label="Executions" value={metrics.total_executions.toString()} />
          <Stat
            label="Compliance rate"
            value={pct(metrics.compliance_rate)}
            tone={meets ? 'ok' : 'warn'}
          />
          <Stat label="Blocked" value={metrics.total_blocked.toString()} tone={metrics.total_blocked ? 'warn' : 'ok'} />
          <Stat label="Fallbacks" value={metrics.total_fallbacks.toString()} />
          <Stat label="Avg reward" value={metrics.avg_reward.toFixed(3)} />
          <Stat label="Avg confidence" value={metrics.avg_confidence.toFixed(2)} />
          <Stat label="Model version" value={`v${metrics.model_version}`} />
        </div>
      </div>

      <div className="card stack">
        <h3 style={{ margin: 0 }}>HITL queue</h3>
        <div className="row" style={{ gap: 24 }}>
          <Stat label="Pending" value={metrics.pending_hitl.toString()} tone={metrics.pending_hitl ? 'warn' : 'ok'} />
          <Stat label="Resolved" value={metrics.resolved_hitl.toString()} />
          <Stat label="Approval rate" value={pct(metrics.approval_rate)} />
        </div>
      </div>

      <div className="card stack">
        <h3 style={{ margin: 0 }}>Per-arm performance</h3>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={th}>Action</th>
              <th style={th}>Label</th>
              <th style={th}>Pulls</th>
              <th style={th}>Avg reward</th>
            </tr>
          </thead>
          <tbody>
            {actions.map((a) => (
              <tr key={a.id}>
                <td style={td}><code>{a.id}</code></td>
                <td style={td}>{a.label}</td>
                <td style={td}>{metrics.arm_pulls[a.id] ?? 0}</td>
                <td style={td}>{(metrics.arm_avg_reward[a.id] ?? 0).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const th: React.CSSProperties = {
  textAlign: 'left',
  padding: '8px 12px',
  borderBottom: '1px solid var(--border)',
  fontWeight: 600,
};
const td: React.CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid var(--border)',
};

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'warn' | 'fail' }) {
  return (
    <div className="stack" style={{ gap: 2, minWidth: 120 }}>
      <div className="muted" style={{ fontSize: '0.85em' }}>{label}</div>
      <div className={`tag ${tone ?? ''}`} style={{ fontSize: '1.05em' }}>{value}</div>
    </div>
  );
}
