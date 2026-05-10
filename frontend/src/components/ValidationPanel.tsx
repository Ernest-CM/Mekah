import type { ValidationSummary } from '../types';

const STATUS_TAG: Record<ValidationSummary['status'], string> = {
  pass: 'ok',
  warn: 'warn',
  fail: 'fail',
};

export default function ValidationPanel({ summary }: { summary: ValidationSummary }) {
  return (
    <div className="card stack" aria-labelledby="validation-h">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3 id="validation-h" style={{ margin: 0 }}>WCAG safety shield</h3>
        <span className={`tag ${STATUS_TAG[summary.status]}`}>{summary.status.toUpperCase()}</span>
      </div>
      <div className="row">
        <span className="tag fail">{summary.hard_failures} hard fail</span>
        <span className="tag warn">{summary.warnings} warn</span>
      </div>
      {summary.violations.length === 0 ? (
        <p className="muted" style={{ margin: 0 }}>No accessibility violations detected.</p>
      ) : (
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          {summary.violations.map((v) => (
            <li key={v.rule_id} style={{ marginBottom: 6 }}>
              <strong>{v.rule_name}</strong> <span className={`tag ${v.severity === 'fail' ? 'fail' : 'warn'}`}>{v.severity}</span>
              <div className="muted" style={{ fontSize: '0.92em' }}>
                {v.message} ({v.sc_reference})
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
