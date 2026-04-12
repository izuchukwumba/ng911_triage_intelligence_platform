import type { ScoreBreakdown } from '../api/client';

interface Props {
  breakdown: ScoreBreakdown[];
  totalScore: number | null;
}

// Tier thresholds — must match scoring-rules.json
const TIER_THRESHOLDS: Array<{ tier: string; min: number; color: string }> = [
  { tier: 'P0', min: 0.85, color: 'var(--p0)' },
  { tier: 'P1', min: 0.65, color: 'var(--p1)' },
  { tier: 'P2', min: 0.40, color: 'var(--p2)' },
  { tier: 'P3', min: 0.20, color: 'var(--p3)' },
];

function activeTierColor(score: number | null): string {
  if (score === null) return 'var(--p4)';
  for (const t of TIER_THRESHOLDS) {
    if (score >= t.min) return t.color;
  }
  return 'var(--p4)';
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div style={{
      fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em',
      textTransform: 'uppercase', color: 'var(--text-muted)',
      padding: '8px 0 4px', borderTop: '1px solid var(--border)', marginTop: '4px',
    }}>{label}</div>
  );
}

interface RowProps {
  item: ScoreBreakdown;
  maxMagnitude: number;
}

function BreakdownRow({ item, maxMagnitude }: RowProps) {
  const isPositive = item.weight >= 0;
  const isPenalty  = item.weight < 0;
  const barColor   = isPenalty ? 'var(--p0)' : item.reason_code === 'DOMAIN_BASE' ? 'var(--accent)' : 'var(--p3)';
  const barWidth   = maxMagnitude > 0 ? Math.abs(item.weight) / maxMagnitude : 0;
  const sign       = isPositive ? '+' : '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', padding: '5px 0', borderBottom: '1px solid rgba(48,54,61,0.5)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: '11px',
          color: isPenalty ? 'var(--p0)' : 'var(--text)',
        }}>
          {item.reason_code}
        </span>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 700,
          color: isPenalty ? 'var(--p0)' : 'var(--p3)',
        }}>
          {sign}{item.weight.toFixed(3)}
        </span>
      </div>

      {/* Bar */}
      <div style={{ height: '3px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${barWidth * 100}%`,
          background: barColor,
          borderRadius: '2px',
          marginLeft: isPenalty ? 'auto' : 0,
          transition: 'width 0.3s ease',
        }} />
      </div>

      <span style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
        {item.description}
      </span>
    </div>
  );
}

function TotalScoreBar({ score }: { score: number | null }) {
  if (score === null) return null;
  const scorePct = Math.max(0, Math.min(100, score * 100));
  const color = activeTierColor(score);

  return (
    <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '10px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)' }}>
          Total Score
        </span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: '15px', fontWeight: 700, color }}>
          {score.toFixed(3)}
        </span>
      </div>

      {/* Threshold labels row */}
      <div style={{ position: 'relative', marginBottom: '4px', height: '14px' }}>
        {TIER_THRESHOLDS.map(({ tier, min, color: tc }) => (
          <span key={tier} style={{
            position: 'absolute',
            left: `${min * 100}%`,
            fontSize: '9px',
            fontFamily: 'var(--mono)',
            color: tc,
            transform: 'translateX(-50%)',
            userSelect: 'none',
          }}>
            {tier}
          </span>
        ))}
      </div>

      {/* Score bar with threshold tick marks */}
      <div style={{ position: 'relative', height: '10px', borderRadius: '5px', overflow: 'visible' }}>
        {/* Background track */}
        <div style={{ position: 'absolute', inset: 0, background: 'var(--border)', borderRadius: '5px' }} />

        {/* Filled score */}
        <div style={{
          position: 'absolute',
          left: 0, top: 0, bottom: 0,
          width: `${scorePct}%`,
          background: color,
          borderRadius: '5px',
          transition: 'width 0.4s ease',
        }} />

        {/* Threshold tick marks */}
        {TIER_THRESHOLDS.map(({ tier, min, color: tc }) => (
          <div key={tier} style={{
            position: 'absolute',
            left: `${min * 100}%`,
            top: '-2px',
            bottom: '-2px',
            width: '2px',
            background: tc,
            opacity: 0.7,
            borderRadius: '1px',
          }} />
        ))}
      </div>

      {/* Scale labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--mono)' }}>
        <span>0</span>
        <span style={{ marginLeft: `${0.20 * 100}%`, transform: 'translateX(-50%)', position: 'relative' }}>0.20</span>
        <span style={{ marginLeft: `${0.40 * 100}%`, transform: 'translateX(-50%)', position: 'relative' }}>0.40</span>
        <span style={{ marginLeft: `${0.65 * 100}%`, transform: 'translateX(-50%)', position: 'relative' }}>0.65</span>
        <span style={{ marginLeft: `${0.85 * 100}%`, transform: 'translateX(-50%)', position: 'relative' }}>0.85</span>
        <span>1.0</span>
      </div>
    </div>
  );
}

export function ScoreBreakdownPanel({ breakdown, totalScore }: Props) {
  if (breakdown.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '12px', padding: '8px 0' }}>
        Score breakdown not available. Run a replay to generate it.
      </div>
    );
  }

  const maxMagnitude = Math.max(0.01, ...breakdown.map((b) => Math.abs(b.weight)));

  const base       = breakdown.filter((b) => b.reason_code === 'DOMAIN_BASE');
  const indicators = breakdown.filter((b) => b.reason_code !== 'DOMAIN_BASE' && b.weight > 0);
  const penalties  = breakdown.filter((b) => b.weight < 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ fontWeight: 600, fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: '4px' }}>
        Score Breakdown
      </div>

      {base.length > 0 && (
        <>
          <SectionLabel label="Domain Base" />
          {base.map((item) => <BreakdownRow key={item.reason_code} item={item} maxMagnitude={maxMagnitude} />)}
        </>
      )}

      {indicators.length > 0 && (
        <>
          <SectionLabel label="Severity Indicators" />
          {indicators.map((item) => <BreakdownRow key={item.reason_code} item={item} maxMagnitude={maxMagnitude} />)}
        </>
      )}

      {penalties.length > 0 && (
        <>
          <SectionLabel label="Penalties" />
          {penalties.map((item) => <BreakdownRow key={item.reason_code} item={item} maxMagnitude={maxMagnitude} />)}
        </>
      )}

      <TotalScoreBar score={totalScore} />
    </div>
  );
}
