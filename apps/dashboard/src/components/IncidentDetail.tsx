import { useCallback, useEffect, useState } from 'react';
import type { AuditEvent, IncidentDetail as Detail, Observation } from '../api/client';
import { api } from '../api/client';
import {
  LOCATION_QUALITY_LABELS,
  POLARITY_LABELS,
  REVIEW_ACTION_LABELS,
  SEVERITY_LABELS,
  STATE_LABELS,
  codeLabel,
} from '../labels';
import { EvidenceText, type Highlight } from './EvidenceText';
import { PriorityBadge } from './PriorityBadge';
import { ReviewPanel } from './ReviewPanel';

interface Props {
  incidentId: string;
  onChanged: () => void;
}

type Tab = 'overview' | 'review' | 'audit';

function isLive(o: Observation): boolean {
  return o.polarity !== 'negated' && o.temporality === 'current';
}

function describe(o: Observation): string {
  const parts = [POLARITY_LABELS[o.polarity] ?? o.polarity];
  if (o.temporality !== 'current') parts.push(o.temporality);
  if (o.attribution === 'second_hand') parts.push('second-hand');
  return `${codeLabel(o.code)} — ${parts.join(', ')}`;
}

export function IncidentDetail({ incidentId, onChanged }: Props) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [focus, setFocus] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState('');

  const load = useCallback(async () => {
    try {
      const [d, e] = await Promise.all([api.getIncident(incidentId), api.getEvents(incidentId)]);
      setDetail(d);
      setEvents(e.events);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [incidentId]);

  useEffect(() => { void load(); }, [load]);

  async function refresh() {
    await load();
    onChanged();
  }

  async function sendFollowUp(e: React.FormEvent) {
    e.preventDefault();
    if (!followUp.trim()) return;
    await api.addMessage(incidentId, followUp.trim());
    setFollowUp('');
    await refresh();
  }

  if (error) return <div role="alert" style={{ padding: '24px', color: 'var(--p0)' }}>{error}</div>;
  if (!detail) return <div className="muted" style={{ padding: '24px' }}>Loading…</div>;

  const { assessment, incident } = detail;
  const failed = assessment.status === 'processing_failed';
  const overridden = detail.effective_priority !== assessment.advisory_priority;
  const observations = incident?.observations ?? [];
  const observationById = new Map(observations.map((o) => [o.observation_id, o]));
  const reviewsOnLatest = detail.reviews.filter((r) => r.assessment_id === assessment.assessment_id);

  return (
    <article aria-label="Incident detail" style={{ height: '100%', overflowY: 'auto', padding: '16px 24px', display: 'grid', gap: '16px', alignContent: 'start' }}>
      <header style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        {failed ? (
          <div role="alert" style={{ border: '1.5px solid var(--p0)', borderRadius: '8px', padding: '10px 16px', color: 'var(--p0)', fontWeight: 700 }}>
            ⚠ PROCESSING FAILED<div style={{ fontSize: '11px', fontWeight: 400 }}>{assessment.failure_reason}</div>
          </div>
        ) : (
          <>
            <PriorityBadge priority={detail.effective_priority} size="lg" caption={overridden ? 'human override' : 'machine suggestion'} />
            {overridden && <PriorityBadge priority={assessment.advisory_priority} size="lg" caption="original machine" />}
          </>
        )}
        <div style={{ display: 'grid', gap: '2px' }}>
          <h2 style={{ fontSize: '16px' }}>
            {incident ? `${codeLabel(incident.classification.domain)}${incident.classification.subtype ? ` · ${codeLabel(incident.classification.subtype)}` : ''}` : 'Unclassified'}
            <span className="muted" style={{ fontSize: '12px', fontWeight: 400 }}> ({incident?.classification.status ?? 'n/a'})</span>
          </h2>
          <span style={{ fontSize: '13px' }}>
            Severity: <strong>{SEVERITY_LABELS[assessment.severity_band]}</strong> · Location: <strong>{LOCATION_QUALITY_LABELS[assessment.location_quality.status]}</strong> · {STATE_LABELS[detail.state]}
          </span>
          <span className="muted mono" style={{ fontSize: '11px' }}>{detail.incident_id} · ruleset {assessment.ruleset_version}</span>
        </div>
      </header>

      <div role="tablist" aria-label="Incident views" style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border)' }}>
        {(['overview', 'review', 'audit'] as Tab[]).map((t) => (
          <button key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => setTab(t)} className={`tab ${tab === t ? 'tab-active' : ''}`}>
            {t === 'overview' ? 'Overview' : t === 'review' ? `Review (${detail.reviews.length})` : `Audit trail (${events.length})`}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          {assessment.review_actions.length > 0 && (
            <section aria-label="Required review actions" className="panel" style={{ borderColor: 'var(--p2)' }}>
              <h3 className="section-title">Needs a human to</h3>
              <ul style={{ paddingLeft: '18px', fontSize: '13px' }}>
                {assessment.review_actions.map((a) => <li key={a}>{REVIEW_ACTION_LABELS[a] ?? a}</li>)}
              </ul>
            </section>
          )}

          <section aria-label="Transcript" className="panel">
            <h3 className="section-title">Transcript (highlighted evidence)</h3>
            {detail.sources.map((s, i) => {
              const highlights: Highlight[] = [
                ...observations
                  .filter((o) => o.evidence.source_event_id === s.source_event_id)
                  .map((o) => ({
                    start: o.evidence.span.start,
                    end: o.evidence.span.end,
                    label: describe(o),
                    muted: !isLive(o),
                    active: focus === o.observation_id,
                  })),
                ...(incident?.locations ?? [])
                  .filter((l) => l.evidence?.source_event_id === s.source_event_id)
                  .map((l) => ({ start: l.evidence!.span.start, end: l.evidence!.span.end, label: 'Reported location', active: focus === l.location_id })),
              ];
              return (
                <div key={s.source_event_id} style={{ marginTop: i ? '8px' : 0 }}>
                  <div className="muted mono" style={{ fontSize: '11px' }}>Message {i + 1} · {new Date(s.received_at).toLocaleTimeString()}</div>
                  <EvidenceText text={s.text} highlights={highlights} />
                </div>
              );
            })}
            <form onSubmit={sendFollowUp} style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <input className="input" style={{ flex: 1 }} aria-label="Follow-up message" placeholder="Add a follow-up message from the caller…" value={followUp} onChange={(e) => setFollowUp(e.target.value)} />
              <button type="submit" className="btn" disabled={!followUp.trim()}>Add</button>
            </form>
          </section>

          <section aria-label="Why this recommendation" className="panel">
            <h3 className="section-title">Why this recommendation?</h3>
            {assessment.reasons.length === 0 && <p className="muted" style={{ fontSize: '13px' }}>No rules fired.</p>}
            <ul style={{ listStyle: 'none', display: 'grid', gap: '6px' }}>
              {assessment.reasons.map((r, i) => (
                <li key={`${r.rule_id}-${i}`} style={{ fontSize: '13px' }}>
                  <span className="mono" style={{ color: 'var(--accent)' }}>{r.rule_id}</span>
                  <span className="muted mono" style={{ fontSize: '11px' }}> v{r.rule_version}</span>{' '}
                  {codeLabel(r.reason_code)}
                  {r.observation_ids.map((id) => {
                    const o = observationById.get(id);
                    return o ? (
                      <button key={id} type="button" className="chip" onMouseEnter={() => setFocus(id)} onMouseLeave={() => setFocus(null)} onFocus={() => setFocus(id)} onBlur={() => setFocus(null)}>
                        “{o.evidence.text}”
                      </button>
                    ) : null;
                  })}
                </li>
              ))}
            </ul>
          </section>

          {incident && (
            <section aria-label="Extracted facts" className="panel">
              <h3 className="section-title">Extracted facts</h3>
              <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                <thead><tr className="muted" style={{ textAlign: 'left' }}><th>Cue</th><th>Status</th><th>Quote</th></tr></thead>
                <tbody>
                  {observations.map((o) => (
                    <tr key={o.observation_id} onMouseEnter={() => setFocus(o.observation_id)} onMouseLeave={() => setFocus(null)} style={{ opacity: isLive(o) ? 1 : 0.6 }}>
                      <td>{codeLabel(o.code)}</td>
                      <td>{describe(o).split(' — ')[1]}</td>
                      <td className="mono">“{o.evidence.text}”</td>
                    </tr>
                  ))}
                  <tr><td>Victim count</td><td>{incident.victim_count.status.replace('_', ' ')}</td><td className="mono">{incident.victim_count.value ?? (incident.victim_count.candidates.join(' or ') || '—')}</td></tr>
                </tbody>
              </table>
              {incident.conflicts.length > 0 && (
                <p style={{ fontSize: '12px', color: 'var(--p2)', marginTop: '6px' }}>
                  ⚠ {incident.conflicts.length} contradiction(s) kept side by side — see highlighted quotes.
                </p>
              )}
            </section>
          )}

          <section aria-label="Locations" className="panel">
            <h3 className="section-title">Reported locations · {LOCATION_QUALITY_LABELS[assessment.location_quality.status]}</h3>
            {(incident?.locations ?? []).length === 0 && <p style={{ fontSize: '13px', color: 'var(--p2)' }}>No location reported — verify with the caller. Severity is not reduced.</p>}
            <ul style={{ listStyle: 'none', display: 'grid', gap: '4px' }}>
              {(incident?.locations ?? []).map((l) => (
                <li key={l.location_id} style={{ fontSize: '13px' }} onMouseEnter={() => setFocus(l.location_id)} onMouseLeave={() => setFocus(null)}>
                  <span className="mono">{l.raw_text}</span>{' '}
                  <span className="muted" style={{ fontSize: '11px' }}>{l.validation}{l.missing_fields.length ? ` · missing ${l.missing_fields.join(', ')}` : ''}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {tab === 'review' && (
        <section aria-label="Review" className="panel" style={{ display: 'grid', gap: '12px' }}>
          {failed ? (
            <p style={{ fontSize: '13px' }}>Processing failed; handle this incident manually from the transcript.</p>
          ) : (
            <ReviewPanel incidentId={incidentId} assessment={assessment} onReviewed={() => void refresh()} />
          )}
          <h3 className="section-title">History</h3>
          {detail.reviews.length === 0 && <p className="muted" style={{ fontSize: '13px' }}>No reviews yet.</p>}
          <ul style={{ listStyle: 'none', display: 'grid', gap: '6px' }}>
            {detail.reviews.map((r) => (
              <li key={r.review_id} style={{ fontSize: '13px', opacity: reviewsOnLatest.includes(r) ? 1 : 0.6 }}>
                <span className="mono muted" style={{ fontSize: '11px' }}>{new Date(r.reviewed_at).toLocaleString()} · {r.reviewer_id}</span>{' '}
                <strong>{codeLabel(r.decision)}</strong>
                {r.override_priority && <> → {r.override_priority}</>}
                {r.reason && <> — {r.reason}</>}
                {!reviewsOnLatest.includes(r) && <span className="muted"> (earlier assessment)</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === 'audit' && (
        <section aria-label="Audit trail" className="panel">
          <ol style={{ listStyle: 'none', display: 'grid', gap: '4px' }}>
            {events.map((e) => (
              <li key={e.event_id} className="mono" style={{ fontSize: '12px' }}>
                <span className="muted">{new Date(e.occurred_at).toLocaleTimeString()}</span>{' '}
                <span style={{ color: 'var(--accent)' }}>{e.event_type}</span>{' '}
                {e.actor.kind}:{e.actor.actor_id}{e.component_version ? ` (${e.component_version})` : ''}
                <span className="muted"> · {e.subject_digest.slice(0, 19)}… · {e.correlation_id}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
    </article>
  );
}
