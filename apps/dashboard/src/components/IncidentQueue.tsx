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

// Reason codes important enough to surface in the queue row
const HIGH_SIGNAL_CODES = new Set([
  'NOT_BREATHING', 'CARDIAC_EVENT', 'VICTIM_UNCONSCIOUS',
  'WEAPON_PRESENT', 'ACTIVE_BLEEDING', 'ACTIVE_VIOLENCE',
  'FIRE_SPREADING', 'MULTIPLE_VICTIMS', 'POSSIBLE_PRANK',
]);

const CODE_SHORT: Record<string, string> = {
  NOT_BREATHING:      'not breathing',
  CARDIAC_EVENT:      'cardiac',
  VICTIM_UNCONSCIOUS: 'unconscious',
  WEAPON_PRESENT:     'weapon',
  ACTIVE_BLEEDING:    'bleeding',
  ACTIVE_VIOLENCE:    'violence',
  FIRE_SPREADING:     'spreading',
  MULTIPLE_VICTIMS:   'multi-victim',
  POSSIBLE_PRANK:     'prank?',
};

// Permanent left-border accent per tier (shows urgency even when unselected)
const TIER_ACCENT_BORDER: Record<string, string> = {
  P0: '3px solid rgba(255,77,79,0.7)',
  P1: '3px solid rgba(255,122,69,0.55)',
  P2: '3px solid rgba(255,169,64,0.4)',
  P3: '3px solid transparent',
  P4: '3px solid transparent',
};

// Subtle background tint per tier — makes queue scannable by color
const TIER_ROW_BG: Record<string, string> = {
  P0: 'rgba(255,77,79,0.06)',
  P1: 'rgba(255,122,69,0.04)',
  P2: 'rgba(255,169,64,0.025)',
  P3: 'transparent',
  P4: 'transparent',
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
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: '13px' }}>Incident Queue</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
          {loading ? 'Refreshing…' : `${incidents.length} incident${incidents.length !== 1 ? 's' : ''}`}
        </span>
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '130px 70px 1fr 64px',
        gap: '8px',
        padding: '5px 16px 5px 19px', // 19px = 16px + 3px border offset
        color: 'var(--text-muted)',
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        borderBottom: '1px solid var(--border)',
      }}>
        <span>Priority</span>
        <span>Domain</span>
        <span>Summary</span>
        <span>Age</span>
      </div>

      {/* Rows */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {incidents.length === 0 && !loading && (
          <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No incidents yet. Submit one via the panel above.
          </div>
        )}

        {incidents.map((inc) => {
          const tier       = inc.triage.priority_tier;
          const isSelected = selectedId === inc.incident_id;

          const surfacedCodes = inc.triage.reason_codes.filter((c) => HIGH_SIGNAL_CODES.has(c));
          const showStress    = inc.caller_context.caller_stress_level === 'high' || inc.caller_context.caller_stress_level === 'moderate';

          return (
            <button
              key={inc.incident_id}
              onClick={() => onSelect(inc.incident_id)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                padding: '9px 16px',
                width: '100%',
                border: 'none',
                borderBottom: '1px solid var(--border)',
                // Selected: accent blue left rail; unselected: tier-colored left rail for P0/P1/P2
                borderLeft: isSelected
                  ? '3px solid var(--accent)'
                  : (TIER_ACCENT_BORDER[tier ?? ''] ?? '3px solid transparent'),
                // Selected: accent tint; unselected: tier tint (P0 red, P1 orange, etc.)
                background: isSelected
                  ? 'rgba(88,166,255,0.07)'
                  : (TIER_ROW_BG[tier ?? ''] ?? 'transparent'),
                color: 'var(--text)',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background 0.12s, border-left-color 0.12s',
              }}
            >
              {/* Main row: grid-aligned */}
              <div style={{ display: 'grid', gridTemplateColumns: '130px 70px 1fr 64px', gap: '8px', alignItems: 'center', width: '100%' }}>
                <PriorityBadge tier={tier} score={inc.triage.priority_score} />

                <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px' }}>
                  <span>{DOMAIN_ICONS[inc.incident.domain] ?? '?'}</span>
                  <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{inc.incident.domain}</span>
                </span>

                <span style={{ fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {inc.incident.summary}
                </span>

                <span style={{ fontSize: '10px', color: 'var(--text-muted)', whiteSpace: 'nowrap', textAlign: 'right' }}>
                  {timeAgo(inc.received_at)}
                </span>
              </div>

              {/* Signal row: reason code chips + stress badge */}
              {(surfacedCodes.length > 0 || showStress) && (
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {surfacedCodes.slice(0, 4).map((code) => {
                    const isPenalty = code === 'POSSIBLE_PRANK';
                    return (
                      <span
                        key={code}
                        style={{
                          padding: '1px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          fontFamily: 'var(--mono)',
                          fontWeight: 600,
                          background: isPenalty ? 'rgba(255,77,79,0.12)' : 'rgba(82,196,26,0.10)',
                          border: `1px solid ${isPenalty ? 'rgba(255,77,79,0.35)' : 'rgba(82,196,26,0.35)'}`,
                          color: isPenalty ? 'var(--p0)' : 'var(--p3)',
                        }}
                      >
                        {CODE_SHORT[code] ?? code.toLowerCase()}
                      </span>
                    );
                  })}

                  {showStress && (
                    <span style={{
                      padding: '1px 6px',
                      borderRadius: '3px',
                      fontSize: '10px',
                      fontWeight: 600,
                      background: 'rgba(255,77,79,0.08)',
                      border: '1px solid rgba(255,77,79,0.25)',
                      color: inc.caller_context.caller_stress_level === 'high' ? 'var(--p0)' : 'var(--p2)',
                    }}>
                      {inc.caller_context.caller_stress_level} stress
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
