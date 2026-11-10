import { useEffect, useState } from 'react';
import type { components } from '../api/schema';
import { api } from '../api/client';

type ReviewComparison = components['schemas']['ReviewComparison'];

const AGREEMENT_LABELS: Record<string, string> = {
  confirmed: 'Confirmed',
  raised: 'Raised by operator',
  lowered: 'Lowered by operator',
  override_same: 'Override, same priority',
  reclassified: 'Reclassified',
  escalated: 'Escalated',
  closed: 'Closed',
  noted: 'Note only',
};

// Human-review replay (design v1.2, section 10.2, mode 4): the machine's
// output next to the operator's decision. Decisions are human judgements,
// never treated as ground truth.
export function ReviewComparisonView() {
  const [comparison, setComparison] = useState<ReviewComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.reviewComparison().then(setComparison).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p role="alert" style={{ color: 'var(--p0)' }}>{error}</p>;
  if (!comparison) return null;

  return (
    <section aria-labelledby="review-comparison-title" className="panel">
      <h3 id="review-comparison-title" className="section-title">
        Machine output vs human review ({comparison.reviewed_assessments} reviewed)
      </h3>
      <p style={{ fontSize: '12px', marginBottom: '8px' }}>
        {Object.entries(comparison.by_agreement)
          .filter(([, n]) => n > 0)
          .map(([k, n]) => `${AGREEMENT_LABELS[k] ?? k}: ${n}`)
          .join(' · ') || 'No reviews yet.'}
      </p>
      {comparison.cases.length > 0 && (
        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
          <caption className="visually-hidden">Each reviewed assessment with the machine output and the operator decision</caption>
          <thead>
            <tr className="muted" style={{ textAlign: 'left' }}>
              <th scope="col">Incident</th><th scope="col">Machine</th><th scope="col">Operator</th>
              <th scope="col">Outcome</th><th scope="col">Reason</th>
            </tr>
          </thead>
          <tbody>
            {comparison.cases.map((c) => (
              <tr key={c.assessment_id}>
                <td className="mono">{c.incident_id.slice(0, 16)}…</td>
                <td>{c.machine_priority ?? '—'} <span className="muted">({c.ruleset_version})</span></td>
                <td>{c.human_priority ?? (c.corrected_domain ? `domain: ${c.corrected_domain}` : c.decision.replace(/_/g, ' '))} <span className="muted">· {c.reviewer_id}</span></td>
                <td>
                  {c.agreement === 'lowered'
                    ? <strong style={{ color: 'var(--p1)' }}>⚠ {AGREEMENT_LABELS[c.agreement]}</strong>
                    : AGREEMENT_LABELS[c.agreement] ?? c.agreement}
                </td>
                <td>{c.reason ?? <span className="muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted" style={{ fontSize: '11px', marginTop: '8px' }}>{comparison.note}</p>
    </section>
  );
}
