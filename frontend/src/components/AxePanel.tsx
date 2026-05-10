import type { AxeResult, AxeViolation } from '../types';

const IMPACT_ORDER: Record<AxeViolation['impact'], number> = {
  critical: 0,
  serious: 1,
  moderate: 2,
  minor: 3,
};

const IMPACT_TAG: Record<AxeViolation['impact'], string> = {
  critical: 'fail',
  serious: 'fail',
  moderate: 'warn',
  minor: 'ok',
};

function sorted(vs: AxeViolation[]) {
  return [...vs].sort((a, b) => IMPACT_ORDER[a.impact] - IMPACT_ORDER[b.impact]);
}

interface Props {
  result: AxeResult | null;
  scanning: boolean;
}

export default function AxePanel({ result, scanning }: Props) {
  const criticalOrSerious = result
    ? result.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious').length
    : 0;
  const status =
    !result || scanning
      ? 'idle'
      : criticalOrSerious > 0
      ? 'fail'
      : result.violations.length > 0
      ? 'warn'
      : 'pass';

  return (
    <div className="card stack" aria-labelledby="axe-h">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3 id="axe-h" style={{ margin: 0 }}>
          axe-core DOM scan
        </h3>
        {scanning ? (
          <span className="tag">scanning…</span>
        ) : status === 'idle' ? (
          <span className="tag muted">not scanned</span>
        ) : (
          <span className={`tag ${status}`}>{status.toUpperCase()}</span>
        )}
      </div>

      {result && !scanning && (
        <>
          <div className="row">
            <span className="tag fail">{result.violations.filter(v => v.impact === 'critical' || v.impact === 'serious').length} critical/serious</span>
            <span className="tag warn">{result.violations.filter(v => v.impact === 'moderate').length} moderate</span>
            <span className="tag ok">{result.passes} rules passed</span>
          </div>

          {result.violations.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>
              No WCAG 2.1 A/AA violations found by axe-core.
            </p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {sorted(result.violations).map((v) => (
                <li key={v.id} style={{ marginBottom: 8 }}>
                  <div className="row" style={{ flexWrap: 'wrap', gap: 4 }}>
                    <strong>{v.help}</strong>
                    <span className={`tag ${IMPACT_TAG[v.impact]}`}>{v.impact}</span>
                    <span className="tag">{v.node_count} node{v.node_count !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="muted" style={{ fontSize: '0.9em', marginTop: 2 }}>
                    {v.sc_references.length > 0
                      ? v.sc_references.join(', ')
                      : `Rule: ${v.id}`}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <p className="muted" style={{ margin: 0, fontSize: '0.82em' }}>
            Scanned at {new Date(result.scanned_at!).toLocaleTimeString()} ·{' '}
            {result.incomplete} rules incomplete · source: axe-core (WCAG 2.1 AA)
          </p>
        </>
      )}
    </div>
  );
}
