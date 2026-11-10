import type { IncidentSummary } from '../api/client';
import { REVIEW_ACTION_LABELS, SEVERITY_LABELS } from '../labels';
import { PriorityBadge } from './PriorityBadge';

interface Props {
  incidents: IncidentSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

const ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };

// Failed processing first (it has no priority but needs urgent attention),
// then by research priority, then newest first.
function rank(i: IncidentSummary): number {
  if (i.processing_status === 'processing_failed') return -1;
  return ORDER[i.advisory_priority ?? ''] ?? 5;
}

export function IncidentQueue({ incidents, selectedId, onSelect, loading }: Props) {
  const sorted = [...incidents].sort(
    (a, b) => rank(a) - rank(b) || b.first_received_at.localeCompare(a.first_received_at),
  );

  return (
    <section aria-label="Incident queue" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '13px', fontWeight: 600 }}>Queue ({incidents.length})</h2>
        <span className="muted" style={{ fontSize: '11px' }}>{loading ? 'refreshing…' : 'suggested review order'}</span>
      </div>
      <ul style={{ listStyle: 'none', overflowY: 'auto', flex: 1 }}>
        {sorted.length === 0 && (
          <li className="muted" style={{ padding: '24px 16px', fontSize: '13px' }}>No incidents yet. Submit a synthetic transcript above.</li>
        )}
        {sorted.map((i) => {
          const failed = i.processing_status === 'processing_failed';
          const selected = i.incident_id === selectedId;
          return (
            <li key={i.incident_id}>
              <button
                type="button"
                onClick={() => onSelect(i.incident_id)}
                aria-current={selected}
                style={{
                  width: '100%', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '4px',
                  padding: '10px 16px', border: 'none', borderBottom: '1px solid var(--border)',
                  background: selected ? 'rgba(88,166,255,0.08)' : 'transparent', color: 'inherit', cursor: 'pointer',
                  borderLeft: `3px solid ${selected ? 'var(--accent)' : 'transparent'}`,
                }}
              >
                <span style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {failed ? (
                    <span style={{ color: 'var(--p0)', fontWeight: 700, fontSize: '12px' }}>⚠ PROCESSING FAILED</span>
                  ) : (
                    <PriorityBadge priority={i.advisory_priority} />
                  )}
                  <span style={{ fontSize: '12px' }}>{SEVERITY_LABELS[i.severity_band ?? ''] ?? '—'} severity</span>
                  <span className="muted mono" style={{ marginLeft: 'auto', fontSize: '11px' }}>
                    {new Date(i.first_received_at).toLocaleTimeString()}
                  </span>
                </span>
                {i.review_actions.length > 0 && (
                  <span className="muted" style={{ fontSize: '11px' }}>
                    {i.review_actions.map((a) => REVIEW_ACTION_LABELS[a] ?? a).join(' · ')}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
