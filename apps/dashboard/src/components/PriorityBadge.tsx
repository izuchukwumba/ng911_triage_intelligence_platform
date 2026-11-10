import { PRIORITY_LABELS, priorityColor } from '../labels';

interface Props {
  priority: string | null | undefined;
  size?: 'sm' | 'lg';
  // Shown under a large badge, e.g. "machine" or "human override".
  caption?: string;
}

// Research-v1 priority labels, not dispatch codes. Always rendered with text.
export function PriorityBadge({ priority, size = 'sm', caption }: Props) {
  const color = priorityColor(priority);
  const label = priority ? PRIORITY_LABELS[priority] ?? priority : 'No priority';

  if (size === 'lg') {
    return (
      <div
        aria-label={`Priority ${priority ?? 'none'}: ${label}`}
        style={{ padding: '10px 16px', borderRadius: '8px', border: `1.5px solid ${color}`, textAlign: 'center', minWidth: '104px' }}
      >
        <div style={{ fontFamily: 'var(--mono)', fontSize: '26px', fontWeight: 800, color, lineHeight: 1 }}>
          {priority ?? '—'}
        </div>
        <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color, marginTop: '5px' }}>
          {label}
        </div>
        {caption && <div className="muted" style={{ fontSize: '10px', marginTop: '4px' }}>{caption}</div>}
      </div>
    );
  }

  return (
    <span
      aria-label={`Priority ${priority ?? 'none'}: ${label}`}
      style={{ display: 'inline-flex', gap: '6px', alignItems: 'center', padding: '2px 8px', borderRadius: '4px', border: `1px solid ${color}`, color, fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap' }}
    >
      {priority ?? '—'}
      <span style={{ fontSize: '10px', opacity: 0.8 }}>{label}</span>
    </span>
  );
}
