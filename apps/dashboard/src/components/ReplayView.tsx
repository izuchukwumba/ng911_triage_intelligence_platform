import { useEffect, useState } from 'react';
import type { components } from '../api/schema';
import { api } from '../api/client';
import { ReviewComparisonView } from './ReviewComparisonView';

type ReplayRun = components['schemas']['ReplayRun'];
type Ruleset = components['schemas']['RulesetOut'];

// Replay comparison (design v1.2, sections 10 and 11.1). Replays never change
// stored incidents; they show what a pinned or candidate ruleset produces.
export function ReplayView() {
  const [rulesets, setRulesets] = useState<Ruleset[]>([]);
  const [candidate, setCandidate] = useState('');
  const [run, setRun] = useState<ReplayRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.rulesets().then(setRulesets).catch((e: Error) => setError(e.message));
    void api.replayRuns().then((runs) => setRun(runs[0] ?? null)).catch(() => undefined);
  }, []);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      setRun(await api.replay({ requested_by: 'operator_1', candidate_ruleset: candidate || null }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Replay" style={{ padding: '16px 24px', overflowY: 'auto', height: '100%', display: 'grid', gap: '12px', alignContent: 'start' }}>
      <div className="panel" style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: '13px' }}>
          Compare against{' '}
          <select className="input" value={candidate} onChange={(e) => setCandidate(e.target.value)}>
            <option value="">— reproducibility check only —</option>
            {rulesets.map((r) => (
              <option key={r.name} value={r.name}>{r.name}{r.default ? ' (default)' : ''}</option>
            ))}
          </select>
        </label>
        <button type="button" className="btn btn-primary" onClick={() => void start()} disabled={busy}>
          {busy ? 'Replaying…' : 'Replay all incidents'}
        </button>
        <span className="muted" style={{ fontSize: '12px' }}>Stored incidents and assessments are never modified.</span>
      </div>
      {error && <p role="alert" style={{ color: 'var(--p0)' }}>{error}</p>}
      {run && (
        <div className="panel">
          <h3 className="section-title">
            Run {run.run_id} · {new Date(run.created_at).toLocaleString()} · engine {run.engine_version}
            {run.candidate_ruleset ? ` · candidate ${run.candidate_ruleset}` : ''}
          </h3>
          <p style={{ fontSize: '13px', marginBottom: '8px' }}>
            {run.summary.reproducible}/{run.summary.incidents - run.summary.skipped} reproducible
            {run.summary.not_reproducible > 0 && <strong style={{ color: 'var(--p0)' }}> · {run.summary.not_reproducible} NOT reproducible</strong>}
            {run.candidate_ruleset && <> · {run.summary.priority_changed} priority changes</>}
            {run.summary.candidate_lowers_priority > 0 && (
              <strong style={{ color: 'var(--p1)' }}> · ⚠ {run.summary.candidate_lowers_priority} would get a LOWER priority</strong>
            )}
            {run.summary.skipped > 0 && <> · {run.summary.skipped} skipped</>}
          </p>
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <thead>
              <tr className="muted" style={{ textAlign: 'left' }}>
                <th>Incident</th><th>Stored</th><th>Reproducible</th><th>Candidate</th><th>Change</th>
              </tr>
            </thead>
            <tbody>
              {run.cases.map((c) => (
                <tr key={c.incident_id}>
                  <td className="mono">{c.incident_id.slice(0, 16)}…</td>
                  <td>{c.stored.advisory_priority ?? '—'} <span className="muted">({c.stored.ruleset_version})</span></td>
                  <td>{c.skipped_reason ? <span className="muted">skipped: {c.skipped_reason}</span> : c.reproducible ? '✓ yes' : '✗ no'}</td>
                  <td>{c.candidate ? `${c.candidate.advisory_priority ?? '—'} (${c.candidate.ruleset_version})` : '—'}</td>
                  <td>
                    {c.candidate_lowers_priority ? <strong style={{ color: 'var(--p1)' }}>lower ⚠</strong>
                      : c.priority_changed ? 'higher' : c.candidate ? 'same' : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ fontSize: '11px', marginTop: '8px' }}>{run.note}</p>
        </div>
      )}
      <ReviewComparisonView />
    </section>
  );
}
