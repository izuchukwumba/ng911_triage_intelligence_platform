import { useState, useEffect, useCallback } from 'react';
import type { IncidentRecord, ScoreBreakdown, IngestResponse } from './api/client';
import { api } from './api/client';
import { IncidentQueue } from './components/IncidentQueue';
import { IncidentDetail } from './components/IncidentDetail';
import { IngestPanel } from './components/IngestPanel';

const POLL_INTERVAL_MS = 8000;

export default function App() {
  const [incidents, setIncidents]           = useState<IncidentRecord[]>([]);
  const [selectedId, setSelectedId]         = useState<string | null>(null);
  const [selectedBreakdown, setSelectedBreakdown] = useState<ScoreBreakdown[]>([]);
  const [loading, setLoading]               = useState(false);
  const [apiStatus, setApiStatus]           = useState<'ok' | 'error' | 'unknown'>('unknown');

  const selectedIncident = incidents.find((i) => i.incident_id === selectedId) ?? null;

  const fetchIncidents = useCallback(async () => {
    setLoading(true);
    try {
      const page = await api.listIncidents({ limit: 100 });
      setIncidents(page.incidents);
      setApiStatus('ok');
    } catch {
      setApiStatus('error');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + polling
  useEffect(() => {
    void fetchIncidents();
    const interval = setInterval(() => { void fetchIncidents(); }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchIncidents]);

  function handleIngested(resp: IngestResponse) {
    setIncidents((prev) => [resp.incident, ...prev]);
    setSelectedId(resp.incident.incident_id);
    setSelectedBreakdown(resp.score_breakdown);
  }

  function handleSelect(id: string) {
    setSelectedId(id);
    setSelectedBreakdown([]);
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Top bar */}
      <header style={{ display: 'flex', alignItems: 'center', padding: '0 20px', height: '48px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', flexShrink: 0, gap: '16px' }}>
        <span style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.02em' }}>NG911 Triage Intelligence</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Decision-Support Platform</span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: apiStatus === 'ok' ? 'var(--p3)' : apiStatus === 'error' ? 'var(--p0)' : 'var(--text-muted)' }} />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {apiStatus === 'ok' ? 'API connected' : apiStatus === 'error' ? 'API unavailable' : 'connecting…'}
          </span>
        </div>
      </header>

      {/* Main layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: queue + ingest */}
        <div style={{ width: '540px', flexShrink: 0, borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <IngestPanel onIngested={handleIngested} />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <IncidentQueue
              incidents={incidents}
              selectedId={selectedId}
              onSelect={handleSelect}
              loading={loading}
            />
          </div>
        </div>

        {/* Right: detail panel */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {selectedIncident ? (
            <IncidentDetail
              key={selectedIncident.incident_id}
              incident={selectedIncident}
              initialBreakdown={selectedBreakdown}
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', flexDirection: 'column', gap: '16px', padding: '32px', textAlign: 'center' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>
                NG911 Triage Intelligence Platform
              </div>
              <div style={{ maxWidth: '340px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.8 }}>
                Submit a transcript on the left to triage it, or select an existing incident to see its priority tier, score breakdown, and the plain-English explanation of why it was classified that way.
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '340px', width: '100%' }}>
                {[
                  { tier: 'P0', label: 'IMMEDIATE', desc: 'Life-threatening', color: 'var(--p0)' },
                  { tier: 'P1', label: 'URGENT',    desc: 'Active danger',    color: 'var(--p1)' },
                  { tier: 'P2', label: 'ELEVATED',  desc: 'Moderate severity',color: 'var(--p2)' },
                  { tier: 'P3', label: 'STANDARD',  desc: 'Low to moderate',  color: 'var(--p3)' },
                  { tier: 'P4', label: 'NON-URGENT',desc: 'Monitor or defer', color: 'var(--p4)' },
                ].map(({ tier, label, desc, color }) => (
                  <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '5px 10px', borderRadius: '5px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '13px', color, minWidth: '24px' }}>{tier}</span>
                    <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color, minWidth: '80px' }}>{label}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
