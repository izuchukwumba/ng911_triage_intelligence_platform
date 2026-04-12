import { useState } from 'react';
import type { IncidentRecord, ScoreBreakdown, ReplayResponse } from '../api/client';
import { api } from '../api/client';
import { PriorityBadge } from './PriorityBadge';
import { ScoreBreakdownPanel } from './ScoreBreakdown';

interface Props {
  incident: IncidentRecord;
  initialBreakdown?: ScoreBreakdown[];
}

// ---------------------------------------------------------------------------
// Plain-English map for reason codes (excluding DOMAIN_BASE)
// ---------------------------------------------------------------------------

const CODE_PROSE: Record<string, string> = {
  NOT_BREATHING:          'patient is not breathing',
  CARDIAC_EVENT:          'cardiac event reported',
  VICTIM_UNCONSCIOUS:     'victim is unconscious',
  WEAPON_PRESENT:         'weapon present at scene',
  ACTIVE_BLEEDING:        'active bleeding reported',
  ACTIVE_VIOLENCE:        'active violence in progress',
  RESPIRATORY_DISTRESS:   'patient in respiratory distress',
  MULTIPLE_VICTIMS:       'multiple victims reported',
  CHILD_INVOLVED:         'child involved',
  CALLER_HIGH_DISTRESS:   'caller is in extreme distress',
  FIRE_SPREADING:         'fire is spreading',
  HAZARDOUS_ENVIRONMENT:  'hazardous environment reported',
  SEIZURE:                'active or recent seizure',
  VICTIM_COUNT_MULTIPLIER:'victim count increases severity',
  POSSIBLE_PRANK:         'possible prank call',
  LOW_LOCATION_CONFIDENCE:'location cannot be reliably dispatched',
  LOW_PARSE_CONFIDENCE:   'transcript could not be parsed with confidence',
};

const TIER_LABELS: Record<string, string> = {
  P0: 'IMMEDIATE',  P1: 'URGENT',  P2: 'ELEVATED',  P3: 'STANDARD',  P4: 'NON-URGENT',
};

const TIER_BG: Record<string, string> = {
  P0: 'rgba(255,77,79,0.08)',
  P1: 'rgba(255,122,69,0.08)',
  P2: 'rgba(255,169,64,0.08)',
  P3: 'rgba(82,196,26,0.08)',
  P4: 'rgba(139,148,158,0.08)',
};

const TIER_COLOR: Record<string, string> = {
  P0: 'var(--p0)',  P1: 'var(--p1)',  P2: 'var(--p2)',  P3: 'var(--p3)',  P4: 'var(--p4)',
};

// ---------------------------------------------------------------------------
// WhyPanel — plain-English triage explanation
// ---------------------------------------------------------------------------

function WhyPanel({ tier, score, breakdown, reasonCodes }: {
  tier: string | null;
  score: number | null;
  breakdown: ScoreBreakdown[];
  reasonCodes: string[];
}) {
  const t = tier ?? '—';
  const color = TIER_COLOR[t] ?? 'var(--text-muted)';
  const bg    = TIER_BG[t]    ?? 'rgba(139,148,158,0.08)';
  const label = TIER_LABELS[t] ?? t;

  // Build prose from breakdown if available, otherwise fall back to reason codes
  let prose: string;

  if (breakdown.length > 0) {
    const positives = breakdown
      .filter((b) => b.weight > 0 && b.reason_code !== 'DOMAIN_BASE')
      .sort((a, b) => b.weight - a.weight);
    const penalties = breakdown.filter((b) => b.weight < 0);

    if (positives.length === 0) {
      // Only base score + maybe penalties
      prose = `Scored ${t} (${score?.toFixed(3) ?? '—'}) from the domain baseline alone.`;
      if (penalties.length > 0) {
        prose += ` Penalised for ${penalties.map((p) => CODE_PROSE[p.reason_code] ?? p.reason_code.toLowerCase()).join(' and ')}.`;
      }
    } else {
      const top = positives.slice(0, 2);
      const topProse = top.map((b) => `${CODE_PROSE[b.reason_code] ?? b.reason_code.toLowerCase()} (+${b.weight.toFixed(2)})`).join(' and ');
      prose = `Classified as ${t} — ${label.toLowerCase()} — primarily because ${topProse}.`;
      if (positives.length > 2) {
        prose += ` ${positives.length - 2} additional indicator${positives.length - 2 > 1 ? 's' : ''} also contributed.`;
      }
      if (penalties.length > 0) {
        prose += ` Penalised for ${penalties.map((p) => CODE_PROSE[p.reason_code] ?? p.reason_code.toLowerCase()).join(' and ')}.`;
      }
    }
  } else if (reasonCodes.filter((c) => c !== 'DOMAIN_BASE').length > 0) {
    const codes = reasonCodes.filter((c) => c !== 'DOMAIN_BASE');
    const proseItems = codes.slice(0, 3).map((c) => CODE_PROSE[c] ?? c.toLowerCase());
    prose = `Classified as ${t} based on: ${proseItems.join(', ')}.`;
  } else {
    prose = `Classified as ${t} (${score?.toFixed(3) ?? '—'}) from the domain baseline with no significant severity indicators.`;
  }

  return (
    <div style={{
      padding: '10px 12px',
      borderRadius: '6px',
      background: bg,
      border: `1px solid ${color}`,
      marginBottom: '14px',
    }}>
      <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color, marginBottom: '5px' }}>
        Why {t} — {label}?
      </div>
      <div style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text)' }}>{prose}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConfidenceMeters — three distinct confidence signals
// ---------------------------------------------------------------------------

function ConfidenceMeter({ label, value, tooltip }: { label: string; value: number; tooltip: string }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.65 ? 'var(--p3)' : value >= 0.35 ? 'var(--p2)' : 'var(--p0)';

  return (
    <div title={tooltip} style={{ flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', marginBottom: '4px' }}>
        <span style={{ color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.03em' }}>{label}</span>
        <span style={{ fontFamily: 'var(--mono)', color, fontWeight: 700 }}>{pct}%</span>
      </div>
      <div style={{ height: '5px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '3px', transition: 'width 0.3s ease' }} />
      </div>
    </div>
  );
}

function ConfidenceMeters({ inc }: { inc: IncidentRecord }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: '8px' }}>
        Confidence Signals
      </div>
      <div style={{ display: 'flex', gap: '16px' }}>
        <ConfidenceMeter
          label="Parse Quality"
          value={inc.incident.confidence}
          tooltip="How well the parser understood this transcript. Low values mean the domain or subtype may be incorrect."
        />
        <ConfidenceMeter
          label="Location (Semantic)"
          value={inc.location.location_confidence}
          tooltip="Confidence that the reported location was understood — not necessarily dispatchable."
        />
        <ConfidenceMeter
          label="Location (Dispatchable)"
          value={inc.location.dispatchable_location_score}
          tooltip="Confidence that emergency services can navigate to this location. Low values trigger the LOW_LOCATION_CONFIDENCE penalty."
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared Field component
// ---------------------------------------------------------------------------

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '7px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontSize: '13px' }}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reason code chips with prominent styling
// ---------------------------------------------------------------------------

function ReasonCodeChips({ codes }: { codes: string[] }) {
  if (codes.length === 0) {
    return <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>none</span>;
  }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginTop: '2px' }}>
      {codes.map((code) => {
        const isPenalty = code.startsWith('LOW_') || code === 'POSSIBLE_PRANK';
        return (
          <span
            key={code}
            title={CODE_PROSE[code] ?? code}
            style={{
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontFamily: 'var(--mono)',
              fontWeight: 600,
              background: isPenalty ? 'rgba(255,77,79,0.12)' : 'rgba(82,196,26,0.12)',
              border: `1px solid ${isPenalty ? 'rgba(255,77,79,0.4)' : 'rgba(82,196,26,0.4)'}`,
              color: isPenalty ? 'var(--p0)' : 'var(--p3)',
              cursor: 'default',
            }}
          >
            {code}
          </span>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audit footer
// ---------------------------------------------------------------------------

function AuditBlock({ inc }: { inc: IncidentRecord }) {
  return (
    <div style={{ marginTop: '12px', padding: '8px 10px', borderRadius: '4px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
      <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '5px' }}>Audit Trail</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text-muted)', lineHeight: 2 }}>
        <div>schema  {inc.audit.schema_version}</div>
        <div>parser  {inc.audit.parser_version ?? '—'}</div>
        <div>scoring {inc.audit.scoring_version ?? '—'}</div>
        <div>at      {inc.audit.processed_at ? new Date(inc.audit.processed_at).toLocaleString() : '—'}</div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function IncidentDetail({ incident: inc, initialBreakdown }: Props) {
  const [breakdown, setBreakdown] = useState<ScoreBreakdown[]>(initialBreakdown ?? []);
  const [replay, setReplay]       = useState<ReplayResponse | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'triage' | 'location' | 'caller' | 'replay'>('triage');

  async function handleReplay() {
    setReplayLoading(true);
    try {
      const result = await api.replay(inc.incident_id);
      setReplay(result);
      setBreakdown(result.score_breakdown);
      setActiveTab('replay');
    } finally {
      setReplayLoading(false);
    }
  }

  const TAB_STYLE = (active: boolean): React.CSSProperties => ({
    padding: '7px 14px',
    border: 'none',
    borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
    background: 'transparent',
    color: active ? 'var(--accent)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: active ? 700 : 400,
    letterSpacing: active ? '0.01em' : 0,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>

      {/* Title bar */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexShrink: 0 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '5px', lineHeight: 1.4 }}>{inc.incident.summary}</div>
          <span style={{ fontFamily: 'var(--mono)', fontSize: '10px', color: 'var(--text-muted)' }}>{inc.incident_id}</span>
        </div>
        <PriorityBadge tier={inc.triage.priority_tier} score={inc.triage.priority_score} />
      </div>

      {/* Raw transcript */}
      <div style={{ padding: '10px 16px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '5px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Transcript</div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--text)', lineHeight: 1.7 }}>{inc.raw_input.text}</div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <button style={TAB_STYLE(activeTab === 'triage')}   onClick={() => setActiveTab('triage')}>Triage</button>
        <button style={TAB_STYLE(activeTab === 'location')} onClick={() => setActiveTab('location')}>Location</button>
        <button style={TAB_STYLE(activeTab === 'caller')}   onClick={() => setActiveTab('caller')}>Caller</button>
        <button style={TAB_STYLE(activeTab === 'replay')}   onClick={() => setActiveTab('replay')}>Replay</button>
      </div>

      {/* Tab content */}
      <div style={{ padding: '14px 16px', flex: 1, overflowY: 'auto' }}>

        {/* ── TRIAGE ── */}
        {activeTab === 'triage' && (
          <div>
            {/* Why this priority? */}
            <WhyPanel
              tier={inc.triage.priority_tier}
              score={inc.triage.priority_score}
              breakdown={breakdown}
              reasonCodes={inc.triage.reason_codes}
            />

            {/* Three confidence signals */}
            <ConfidenceMeters inc={inc} />

            {/* Key fields */}
            <Field label="Domain" value={
              <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{inc.incident.domain}</span>
            } />
            <Field label="Subtype" value={
              <span style={{ textTransform: 'capitalize' }}>{inc.incident.subtype.replace(/_/g, ' ')}</span>
            } />
            <Field label="Victim Count" value={
              inc.incident.victim_count_estimate !== null
                ? String(inc.incident.victim_count_estimate)
                : <span style={{ color: 'var(--text-muted)' }}>unknown</span>
            } />
            <Field label="Reason Codes" value={
              <ReasonCodeChips codes={inc.triage.reason_codes} />
            } />

            {/* Score breakdown */}
            <div style={{ marginTop: '16px' }}>
              <ScoreBreakdownPanel breakdown={breakdown} totalScore={inc.triage.priority_score} />
            </div>
          </div>
        )}

        {/* ── LOCATION ── */}
        {activeTab === 'location' && (
          <div>
            <Field label="Address Text" value={
              inc.location.address_text
                ?? <span style={{ color: 'var(--text-muted)' }}>none detected</span>
            } />
            <Field label="Coordinates" value={
              inc.location.lat !== null
                ? `${inc.location.lat}, ${inc.location.lng}`
                : <span style={{ color: 'var(--text-muted)' }}>none</span>
            } />

            <div style={{ marginTop: '14px', marginBottom: '4px' }}>
              <ConfidenceMeter
                label="Location Confidence (Semantic)"
                value={inc.location.location_confidence}
                tooltip="Confidence that the reported location was understood semantically."
              />
            </div>
            <div style={{ marginTop: '10px' }}>
              <ConfidenceMeter
                label="Dispatchable Location Score"
                value={inc.location.dispatchable_location_score}
                tooltip="Confidence that emergency services can navigate to this location. Below 0.30 triggers the LOW_LOCATION_CONFIDENCE penalty."
              />
            </div>

            {inc.location.dispatchable_location_score < 0.30 && (
              <div style={{ marginTop: '10px', padding: '8px 10px', borderRadius: '4px', background: 'rgba(255,77,79,0.08)', border: '1px solid rgba(255,77,79,0.3)', fontSize: '12px', color: 'var(--p0)' }}>
                LOW_LOCATION_CONFIDENCE penalty applied (−0.08). This location may not be navigable by emergency services.
              </div>
            )}

            {inc.location.validation_notes.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>Validation Notes</div>
                {inc.location.validation_notes.map((n, i) => (
                  <div key={i} style={{ padding: '5px 8px', background: 'rgba(255,122,69,0.08)', border: '1px solid rgba(255,122,69,0.3)', borderRadius: '4px', fontSize: '12px', marginBottom: '4px', color: 'var(--p1)' }}>
                    {n}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── CALLER ── */}
        {activeTab === 'caller' && (
          <div>
            <Field label="Language" value={
              inc.caller_context.language_hint
                ? <span style={{ fontFamily: 'var(--mono)', fontWeight: 600 }}>{inc.caller_context.language_hint}</span>
                : <span style={{ color: 'var(--text-muted)' }}>—</span>
            } />
            <Field label="Stress Level" value={
              inc.caller_context.caller_stress_level
                ? <span style={{
                    textTransform: 'capitalize',
                    fontWeight: 700,
                    color: inc.caller_context.caller_stress_level === 'high'
                      ? 'var(--p0)'
                      : inc.caller_context.caller_stress_level === 'moderate'
                        ? 'var(--p2)'
                        : 'var(--p3)',
                  }}>
                    {inc.caller_context.caller_stress_level}
                  </span>
                : <span style={{ color: 'var(--text-muted)' }}>not detected</span>
            } />
            <Field label="Background Noise" value={
              inc.caller_context.background_noise_level
                ?? <span style={{ color: 'var(--text-muted)' }}>—</span>
            } />

            {inc.caller_context.caller_stress_level === 'high' && (
              <div style={{ marginTop: '10px', padding: '8px 10px', borderRadius: '4px', background: 'rgba(255,77,79,0.08)', border: '1px solid rgba(255,77,79,0.3)', fontSize: '12px', color: 'var(--p0)' }}>
                CALLER_HIGH_DISTRESS detected. Extreme stress signals (repetition, all-caps, fragmented speech) were found in the transcript. Added +0.08 to the priority score.
              </div>
            )}

            <AuditBlock inc={inc} />
          </div>
        )}

        {/* ── REPLAY ── */}
        {activeTab === 'replay' && (
          <div>
            {!replay && (
              <div style={{ padding: '28px 0', textAlign: 'center' }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: '6px', fontSize: '13px', lineHeight: 1.6 }}>
                  Re-run the full parse and score pipeline against this incident's original transcript.
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginBottom: '16px' }}>
                  Differences in the result reflect changes to parser or scoring rules since this incident was ingested.
                </div>
                <button
                  onClick={handleReplay}
                  disabled={replayLoading}
                  style={{ padding: '8px 22px', background: 'var(--accent)', color: '#0d1117', border: 'none', borderRadius: '6px', fontWeight: 700, cursor: 'pointer', opacity: replayLoading ? 0.6 : 1, fontSize: '13px' }}
                >
                  {replayLoading ? 'Replaying…' : 'Run Replay'}
                </button>
              </div>
            )}

            {replay && (
              <div>
                {/* Original vs Replayed */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                  <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>Original</div>
                    <PriorityBadge tier={replay.original.triage.priority_tier} score={replay.original.triage.priority_score} />
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: '6px' }}>
                      scoring v{replay.original.audit.scoring_version ?? '—'}
                    </div>
                  </div>
                  <div style={{ padding: '10px 12px', background: 'rgba(88,166,255,0.05)', borderRadius: '6px', border: '1px solid rgba(88,166,255,0.3)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--accent)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>Replayed</div>
                    <PriorityBadge tier={replay.replayed.triage.priority_tier} score={replay.replayed.triage.priority_score} />
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: '6px' }}>
                      scoring v{replay.replayed.audit.scoring_version ?? '—'}
                    </div>
                  </div>
                </div>

                {/* Diff status */}
                <div style={{
                  padding: '8px 12px', borderRadius: '6px', marginBottom: '14px', fontSize: '12px',
                  background: replay.diff.priority_tier_changed ? 'rgba(255,169,64,0.08)' : 'rgba(82,196,26,0.08)',
                  border: `1px solid ${replay.diff.priority_tier_changed ? 'var(--p2)' : 'var(--p3)'}`,
                  color: replay.diff.priority_tier_changed ? 'var(--p2)' : 'var(--p3)',
                }}>
                  {replay.diff.priority_tier_changed
                    ? `Tier changed: ${replay.original.triage.priority_tier} → ${replay.replayed.triage.priority_tier}  |  score Δ ${replay.diff.score_delta >= 0 ? '+' : ''}${replay.diff.score_delta.toFixed(3)}`
                    : `No tier change  |  score Δ ${replay.diff.score_delta >= 0 ? '+' : ''}${replay.diff.score_delta.toFixed(3)}`
                  }
                </div>

                {/* Code diffs */}
                {replay.diff.reason_codes_added.length > 0 && (
                  <Field label="Reason Codes Added" value={
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                      {replay.diff.reason_codes_added.map((c) => (
                        <span key={c} style={{ padding: '2px 7px', background: 'rgba(82,196,26,0.12)', border: '1px solid rgba(82,196,26,0.4)', borderRadius: '4px', fontSize: '11px', color: 'var(--p3)', fontFamily: 'var(--mono)', fontWeight: 600 }}>{c}</span>
                      ))}
                    </div>
                  } />
                )}
                {replay.diff.reason_codes_removed.length > 0 && (
                  <Field label="Reason Codes Removed" value={
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                      {replay.diff.reason_codes_removed.map((c) => (
                        <span key={c} style={{ padding: '2px 7px', background: 'rgba(255,77,79,0.12)', border: '1px solid rgba(255,77,79,0.4)', borderRadius: '4px', fontSize: '11px', color: 'var(--p0)', fontFamily: 'var(--mono)', fontWeight: 600 }}>{c}</span>
                      ))}
                    </div>
                  } />
                )}

                {/* Replayed breakdown */}
                <div style={{ marginTop: '16px' }}>
                  <ScoreBreakdownPanel breakdown={replay.score_breakdown} totalScore={replay.replayed.triage.priority_score} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
