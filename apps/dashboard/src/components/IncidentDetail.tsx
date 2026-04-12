import { useState } from 'react';
import type { IncidentRecord, ScoreBreakdown, ReplayResponse } from '../api/client';
import { api } from '../api/client';
import { PriorityBadge } from './PriorityBadge';
import { ScoreBreakdownPanel } from './ScoreBreakdown';

interface Props {
  incident: IncidentRecord;
  initialBreakdown?: ScoreBreakdown[];
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
      <span style={{ fontSize: '13px' }}>{value}</span>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.6 ? 'var(--p2)' : value >= 0.3 ? 'var(--p3)' : 'var(--p0)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', marginBottom: '6px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--mono)', color }}>{pct}%</span>
      </div>
      <div style={{ height: '5px', background: 'var(--border)', borderRadius: '3px' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '3px' }} />
      </div>
    </div>
  );
}

export function IncidentDetail({ incident: inc, initialBreakdown }: Props) {
  const [breakdown, setBreakdown] = useState<ScoreBreakdown[]>(initialBreakdown ?? []);
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
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
    padding: '6px 14px',
    border: 'none',
    borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
    background: 'transparent',
    color: active ? 'var(--accent)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: active ? 600 : 400,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      {/* Title bar */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '15px', marginBottom: '4px' }}>{inc.incident.summary}</div>
          <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text-muted)' }}>{inc.incident_id}</span>
        </div>
        <PriorityBadge tier={inc.triage.priority_tier} score={inc.triage.priority_score} />
      </div>

      {/* Raw transcript */}
      <div style={{ padding: '10px 16px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Raw Transcript</div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: '12px', color: 'var(--text)', lineHeight: 1.6 }}>{inc.raw_input.text}</div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)' }}>
        <button style={TAB_STYLE(activeTab === 'triage')}   onClick={() => setActiveTab('triage')}>Triage</button>
        <button style={TAB_STYLE(activeTab === 'location')} onClick={() => setActiveTab('location')}>Location</button>
        <button style={TAB_STYLE(activeTab === 'caller')}   onClick={() => setActiveTab('caller')}>Caller</button>
        <button style={TAB_STYLE(activeTab === 'replay')}   onClick={() => setActiveTab('replay')}>Replay</button>
      </div>

      <div style={{ padding: '12px 16px', flex: 1 }}>
        {activeTab === 'triage' && (
          <div>
            <Field label="Domain" value={<span style={{ textTransform: 'capitalize' }}>{inc.incident.domain}</span>} />
            <Field label="Subtype" value={inc.incident.subtype.replace(/_/g, ' ')} />
            <Field label="Parser Confidence" value={`${Math.round(inc.incident.confidence * 100)}%`} />
            <Field label="Severity Indicators" value={
              inc.incident.severity_indicators.length > 0
                ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                    {inc.incident.severity_indicators.map((si) => (
                      <span key={si} style={{ padding: '2px 6px', background: 'rgba(255,77,79,0.15)', border: '1px solid var(--p0)', borderRadius: '3px', fontSize: '11px', color: 'var(--p0)', fontFamily: 'var(--mono)' }}>{si}</span>
                    ))}
                  </div>
                : <span style={{ color: 'var(--text-muted)' }}>none</span>
            } />
            <Field label="Victim Count" value={inc.incident.victim_count_estimate ?? 'unknown'} />
            <div style={{ marginTop: '16px' }}>
              <ScoreBreakdownPanel breakdown={breakdown} totalScore={inc.triage.priority_score} />
            </div>
          </div>
        )}

        {activeTab === 'location' && (
          <div>
            <Field label="Address Text" value={inc.location.address_text ?? <span style={{ color: 'var(--text-muted)' }}>none detected</span>} />
            <Field label="Coordinates" value={inc.location.lat !== null ? `${inc.location.lat}, ${inc.location.lng}` : <span style={{ color: 'var(--text-muted)' }}>none</span>} />
            <div style={{ marginTop: '12px' }}>
              <ScoreBar label="Location Confidence"          value={inc.location.location_confidence} />
              <ScoreBar label="Dispatchable Location Score"  value={inc.location.dispatchable_location_score} />
            </div>
            {inc.location.validation_notes.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '6px' }}>Validation Notes</div>
                {inc.location.validation_notes.map((n, i) => (
                  <div key={i} style={{ padding: '4px 8px', background: 'rgba(255,122,69,0.1)', border: '1px solid rgba(255,122,69,0.3)', borderRadius: '3px', fontSize: '12px', marginBottom: '4px', color: 'var(--p1)' }}>{n}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'caller' && (
          <div>
            <Field label="Language" value={inc.caller_context.language_hint ?? '—'} />
            <Field label="Stress Level" value={inc.caller_context.caller_stress_level
              ? <span style={{ textTransform: 'capitalize', color: inc.caller_context.caller_stress_level === 'high' ? 'var(--p0)' : inc.caller_context.caller_stress_level === 'moderate' ? 'var(--p2)' : 'var(--p3)' }}>{inc.caller_context.caller_stress_level}</span>
              : <span style={{ color: 'var(--text-muted)' }}>not detected</span>}
            />
            <Field label="Background Noise" value={inc.caller_context.background_noise_level ?? <span style={{ color: 'var(--text-muted)' }}>—</span>} />
            <div style={{ marginTop: '12px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '4px' }}>AUDIT</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.8 }}>
                <div>schema: {inc.audit.schema_version}</div>
                <div>parser: {inc.audit.parser_version ?? '—'}</div>
                <div>scoring: {inc.audit.scoring_version ?? '—'}</div>
                <div>processed: {inc.audit.processed_at ? new Date(inc.audit.processed_at).toLocaleString() : '—'}</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'replay' && (
          <div>
            {!replay && (
              <div style={{ textAlign: 'center', padding: '32px 0' }}>
                <div style={{ color: 'var(--text-muted)', marginBottom: '12px', fontSize: '13px' }}>
                  Re-parse and re-score this incident with the current parser and scoring config.
                </div>
                <button
                  onClick={handleReplay}
                  disabled={replayLoading}
                  style={{ padding: '8px 20px', background: 'var(--accent)', color: '#0d1117', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: 'pointer', opacity: replayLoading ? 0.6 : 1 }}
                >
                  {replayLoading ? 'Replaying…' : 'Run Replay'}
                </button>
              </div>
            )}

            {replay && (
              <div>
                <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
                  <div style={{ flex: 1, padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>ORIGINAL</div>
                    <PriorityBadge tier={replay.original.triage.priority_tier} score={replay.original.triage.priority_score} />
                  </div>
                  <div style={{ flex: 1, padding: '10px', background: 'rgba(88,166,255,0.05)', borderRadius: '6px', border: '1px solid rgba(88,166,255,0.3)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>REPLAYED</div>
                    <PriorityBadge tier={replay.replayed.triage.priority_tier} score={replay.replayed.triage.priority_score} />
                  </div>
                </div>

                <div style={{ padding: '8px 12px', borderRadius: '6px', background: replay.diff.priority_tier_changed ? 'rgba(255,169,64,0.1)' : 'rgba(82,196,26,0.1)', border: `1px solid ${replay.diff.priority_tier_changed ? 'var(--p2)' : 'var(--p3)'}`, marginBottom: '16px', fontSize: '12px' }}>
                  {replay.diff.priority_tier_changed
                    ? `Tier changed: ${replay.original.triage.priority_tier} → ${replay.replayed.triage.priority_tier} (Δ ${replay.diff.score_delta >= 0 ? '+' : ''}${replay.diff.score_delta.toFixed(3)})`
                    : `No tier change (score Δ ${replay.diff.score_delta >= 0 ? '+' : ''}${replay.diff.score_delta.toFixed(3)})`}
                </div>

                {replay.diff.reason_codes_added.length > 0 && (
                  <Field label="Reason Codes Added" value={<div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>{replay.diff.reason_codes_added.map((c) => <span key={c} style={{ padding: '2px 6px', background: 'rgba(82,196,26,0.15)', border: '1px solid var(--p3)', borderRadius: '3px', fontSize: '11px', color: 'var(--p3)', fontFamily: 'var(--mono)' }}>{c}</span>)}</div>} />
                )}
                {replay.diff.reason_codes_removed.length > 0 && (
                  <Field label="Reason Codes Removed" value={<div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>{replay.diff.reason_codes_removed.map((c) => <span key={c} style={{ padding: '2px 6px', background: 'rgba(255,77,79,0.15)', border: '1px solid var(--p0)', borderRadius: '3px', fontSize: '11px', color: 'var(--p0)', fontFamily: 'var(--mono)' }}>{c}</span>)}</div>} />
                )}

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
