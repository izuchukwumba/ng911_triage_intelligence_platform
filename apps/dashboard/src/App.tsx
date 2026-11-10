import { useCallback, useEffect, useState } from 'react';
import type { IncidentSummary, IngestOut } from './api/client';
import { api } from './api/client';
import { IncidentDetail } from './components/IncidentDetail';
import { IncidentQueue } from './components/IncidentQueue';
import { IngestPanel } from './components/IngestPanel';
import { ReplayView } from './components/ReplayView';
import { SimulationBanner } from './components/SimulationBanner';

const POLL_INTERVAL_MS = 8000;

export default function App() {
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState<'ok' | 'error' | 'unknown'>('unknown');
  // Bumped to make the detail view reload after the queue changes.
  const [revision, setRevision] = useState(0);
  const [view, setView] = useState<'queue' | 'replay'>('queue');

  const fetchIncidents = useCallback(async () => {
    setLoading(true);
    try {
      const page = await api.listIncidents(100);
      setIncidents(page.items);
      setApiStatus('ok');
    } catch {
      setApiStatus('error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchIncidents();
    const interval = setInterval(() => void fetchIncidents(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchIncidents]);

  function handleIngested(result: IngestOut) {
    setSelectedId(result.incident_id);
    setRevision((r) => r + 1);
    void fetchIncidents();
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <SimulationBanner />
      <header style={{ display: 'flex', alignItems: 'center', padding: '0 20px', height: '44px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', gap: '16px', flexShrink: 0 }}>
        <h1 style={{ fontWeight: 700, fontSize: '15px' }}>NG911 Triage Intelligence</h1>
        <span className="muted" style={{ fontSize: '12px' }}>Research decision-support · human in the loop</span>
        <nav aria-label="Views" style={{ display: 'flex', gap: '4px', marginLeft: '16px' }}>
          <button type="button" className={`tab ${view === 'queue' ? 'tab-active' : ''}`} aria-pressed={view === 'queue'} onClick={() => setView('queue')}>Queue</button>
          <button type="button" className={`tab ${view === 'replay' ? 'tab-active' : ''}`} aria-pressed={view === 'replay'} onClick={() => setView('replay')}>Replay</button>
        </nav>
        <span role="status" style={{ marginLeft: 'auto', fontSize: '11px' }} className="muted">
          {apiStatus === 'ok' ? '● API connected' : apiStatus === 'error' ? '○ API unavailable' : 'connecting…'}
        </span>
      </header>
      {view === 'replay' ? (
        <main style={{ flex: 1, overflow: 'hidden' }}><ReplayView /></main>
      ) : (
      <main style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '460px', flexShrink: 0, borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <IngestPanel onIngested={handleIngested} />
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <IncidentQueue incidents={incidents} selectedId={selectedId} onSelect={setSelectedId} loading={loading} />
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {selectedId ? (
            <IncidentDetail key={`${selectedId}:${revision}`} incidentId={selectedId} onChanged={() => void fetchIncidents()} />
          ) : (
            <div className="muted" style={{ padding: '24px', fontSize: '13px' }}>Select an incident to see its evidence, recommendation and review history.</div>
          )}
        </div>
      </main>
      )}
    </div>
  );
}
