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
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '32px' }}>←</span>
              <span>Select an incident to view details</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
