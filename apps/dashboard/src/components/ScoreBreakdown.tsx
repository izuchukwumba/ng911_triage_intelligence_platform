import type { ScoreBreakdown } from '../api/client';

interface Props {
  breakdown: ScoreBreakdown[];
  totalScore: number | null;
}

export function ScoreBreakdownPanel({ breakdown, totalScore }: Props) {
  const maxAbsWeight = Math.max(0.01, ...breakdown.map((b) => Math.abs(b.weight)));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontWeight: 600, fontSize: '13px' }}>Score Breakdown</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: '13px', color: 'var(--accent)' }}>
          Final: {totalScore?.toFixed(3) ?? '—'}
        </span>
      </div>

      {breakdown.map((item) => {
        const isPositive = item.weight >= 0;
        const barColor = isPositive ? 'var(--accent)' : 'var(--p0)';
        const barWidth = Math.abs(item.weight) / maxAbsWeight;

        return (
          <div key={item.reason_code} style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: isPositive ? 'var(--text)' : 'var(--p0)' }}>
                {item.reason_code}
              </span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 600, color: isPositive ? 'var(--accent)' : 'var(--p0)' }}>
                {isPositive ? '+' : ''}{item.weight.toFixed(3)}
              </span>
            </div>

            {/* Bar chart */}
            <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${barWidth * 100}%`,
                background: barColor,
                borderRadius: '2px',
                marginLeft: isPositive ? 0 : 'auto',
                transition: 'width 0.3s ease',
              }} />
            </div>

            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {item.description}
            </span>
          </div>
        );
      })}
    </div>
  );
}
