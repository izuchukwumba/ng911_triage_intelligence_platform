import { useState } from 'react';
import type { Assessment, Priority, ReviewIn } from '../api/client';
import { api } from '../api/client';
import { PRIORITY_LABELS } from '../labels';

interface Props {
  incidentId: string;
  assessment: Assessment;
  onReviewed: () => void;
}

type Decision = ReviewIn['decision'];

const DECISIONS: { value: Decision; label: string }[] = [
  { value: 'confirm', label: 'Confirm assessment' },
  { value: 'override_priority', label: 'Override priority' },
  { value: 'escalate', label: 'Escalate' },
  { value: 'note', label: 'Add note' },
];

// Records a human decision. The machine assessment is never changed: the
// review is stored separately and shown next to it (design v1.2, 11.1).
export function ReviewPanel({ incidentId, assessment, onReviewed }: Props) {
  const [decision, setDecision] = useState<Decision>('confirm');
  const [priority, setPriority] = useState<Priority>('P1');
  const [reason, setReason] = useState('');
  const [reviewer, setReviewer] = useState('operator_1');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const needsReason = decision !== 'confirm' && decision !== 'escalate';

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.review(incidentId, {
        assessment_id: assessment.assessment_id,
        reviewer_id: reviewer,
        decision,
        reason: reason.trim() || null,
        override_priority: decision === 'override_priority' ? priority : null,
      });
      setReason('');
      onReviewed();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} aria-label="Human review" style={{ display: 'grid', gap: '8px' }}>
      <fieldset style={{ border: 'none', display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
        <legend className="section-title">Decision</legend>
        {DECISIONS.map((d) => (
          <label key={d.value} style={{ display: 'flex', gap: '4px', alignItems: 'center', fontSize: '13px' }}>
            <input type="radio" name="decision" value={d.value} checked={decision === d.value} onChange={() => setDecision(d.value)} />
            {d.label}
          </label>
        ))}
      </fieldset>
      {decision === 'override_priority' && (
        <label style={{ fontSize: '13px' }}>
          New priority{' '}
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)} className="input">
            {Object.entries(PRIORITY_LABELS).map(([p, label]) => (
              <option key={p} value={p}>{p} — {label}</option>
            ))}
          </select>
        </label>
      )}
      <label style={{ fontSize: '13px', display: 'grid', gap: '4px' }}>
        Reason{needsReason ? ' (required)' : ' (optional)'}
        <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required={needsReason} />
      </label>
      <label style={{ fontSize: '13px' }}>
        Reviewer id <input className="input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} required pattern="[A-Za-z0-9_.:-]+" />
      </label>
      {error && <span role="alert" style={{ color: 'var(--p0)', fontSize: '12px' }}>{error}</span>}
      <button type="submit" className="btn btn-primary" disabled={saving} style={{ justifySelf: 'start' }}>
        {saving ? 'Saving…' : 'Record review'}
      </button>
    </form>
  );
}
