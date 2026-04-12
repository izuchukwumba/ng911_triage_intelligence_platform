interface Props {
  tier: string | null;
  score?: number | null;
}

const TIER_COLORS: Record<string, string> = {
  P0: 'var(--p0)',
  P1: 'var(--p1)',
  P2: 'var(--p2)',
  P3: 'var(--p3)',
  P4: 'var(--p4)',
};

const TIER_LABELS: Record<string, string> = {
  P0: 'IMMEDIATE',
  P1: 'URGENT',
  P2: 'ELEVATED',
  P3: 'STANDARD',
  P4: 'NON-URGENT',
};

export function PriorityBadge({ tier, score }: Props) {
  const color = TIER_COLORS[tier ?? ''] ?? 'var(--text-muted)';
  const label = TIER_LABELS[tier ?? ''] ?? tier ?? '—';

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
