interface Props {
  tier: string | null;
  score?: number | null;
  size?: 'sm' | 'lg';
}

const TIER_COLORS: Record<string, string> = {
  P0: 'var(--p0)',
  P1: 'var(--p1)',
  P2: 'var(--p2)',
  P3: 'var(--p3)',
  P4: 'var(--p4)',
};

const TIER_BG: Record<string, string> = {
  P0: 'rgba(255,77,79,0.12)',
  P1: 'rgba(255,122,69,0.10)',
  P2: 'rgba(255,169,64,0.10)',
  P3: 'rgba(82,196,26,0.08)',
  P4: 'rgba(139,148,158,0.06)',
};

const TIER_LABELS: Record<string, string> = {
  P0: 'IMMEDIATE',
  P1: 'URGENT',
  P2: 'ELEVATED',
  P3: 'STANDARD',
  P4: 'NON-URGENT',
};

export function PriorityBadge({ tier, score, size = 'sm' }: Props) {
  const color = TIER_COLORS[tier ?? ''] ?? 'var(--text-muted)';
  const bg    = TIER_BG[tier ?? '']    ?? 'rgba(139,148,158,0.06)';
  const label = TIER_LABELS[tier ?? ''] ?? tier ?? '—';

  // Large variant — used in the incident detail header
  if (size === 'lg') {
    return (
      <div style={{
        padding: '10px 16px',
        borderRadius: '8px',
        border: `1.5px solid ${color}`,
        background: bg,
        textAlign: 'center',
        minWidth: '96px',
        flexShrink: 0,
      }}>
        <div style={{
          fontFamily: 'var(--mono)',
          fontSize: '26px',
          fontWeight: 800,
          color,
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}>
          {tier ?? '—'}
        </div>
        <div style={{
          fontSize: '9px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color,
          opacity: 0.85,
          marginTop: '5px',
        }}>
          {label}
        </div>
        {score !== undefined && score !== null && (
          <div style={{
            fontFamily: 'var(--mono)',
            fontSize: '11px',
            color: 'var(--text-muted)',
            marginTop: '4px',
          }}>
            {score.toFixed(3)}
          </div>
        )}
      </div>
    );
  }

  // Small variant — used in the queue rows (default)
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '2px 8px',
      borderRadius: '4px',
      border: `1px solid ${color}`,
      color,
      fontFamily: 'var(--mono)',
      fontSize: '12px',
      fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {tier ?? '—'}
      {score !== undefined && score !== null && (
        <span style={{ opacity: 0.75, fontWeight: 400 }}>
          {score.toFixed(2)}
        </span>
      )}
      <span style={{ fontSize: '10px', opacity: 0.65 }}>{label}</span>
    </span>
  );
}
