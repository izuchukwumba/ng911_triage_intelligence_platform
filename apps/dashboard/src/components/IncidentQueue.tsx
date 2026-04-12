import type { IncidentRecord } from '../api/client';
import { PriorityBadge } from './PriorityBadge';

interface Props {
  incidents: IncidentRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

const DOMAIN_ICONS: Record<string, string> = {
  police: '🚓',  fire: '🔥',  ems: '🚑',  hazmat: '☣',
  other: '⚠',   unknown: '?',
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export function IncidentQueue({ incidents, selectedId, onSelect, loading }: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600 }}>Incident Queue</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
          {loading ? 'Refreshing…' : `${incidents.length} incidents`}
        </span>
      </div>

      {/* Column headers */}
      <div style={{ display: 'grid', gridTemplateColumns: '140px 80px 1fr 80px', gap: '8px', padding: '6px 16px', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid var(--border)' }}>
        <span>Priority</span>
        <span>Domain</span>
        <span>Summary</span>
        <span>Received</span>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {incidents.length === 0 && !loading && (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No incidents yet. Submit one via <code>POST /ingest</code>.
          </div>
        )}

        {incidents.map((inc) => (
          <button
            key={inc.incident_id}
            onClick={() => onSelect(inc.incident_id)}
            style={{
              display: 'grid',
              gridTemplateColumns: '140px 80px 1fr 80px',
              gap: '8px',
              padding: '10px 16px',
              width: '100%',
              border: 'none',
              borderBottom: '1px solid var(--border)',
              background: selectedId === inc.incident_id ? 'rgba(88,166,255,0.08)' : 'transparent',
              color: 'var(--text)',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background 0.15s',
            }}
          >
            <PriorityBadge tier={inc.triage.priority_tier} score={inc.triage.priority_score} />

            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '13px' }}>
              <span>{DOMAIN_ICONS[inc.incident.domain] ?? '?'}</span>
              <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{inc.incident.domain}</span>
            </span>

            <span style={{ fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', alignSelf: 'center' }}>
              {inc.incident.summary}
            </span>

            <span style={{ fontSize: '11px', color: 'var(--text-muted)', alignSelf: 'center', whiteSpace: 'nowrap' }}>
              {timeAgo(inc.received_at)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
