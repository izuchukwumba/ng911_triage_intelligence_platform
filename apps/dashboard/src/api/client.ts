const BASE = '';  // proxied through Vite to http://localhost:3001

export interface IncidentRecord {
  incident_id: string;
  received_at: string;
  source_type: string;
  raw_input: { text: string };
  incident: {
    domain: string;
    subtype: string;
    summary: string;
    severity_indicators: string[];
    victim_count_estimate: number | null;
    confidence: number;
  };
  location: {
    address_text: string | null;
    lat: number | null;
    lng: number | null;
    location_confidence: number;
    dispatchable_location_score: number;
    validation_notes: string[];
  };
  caller_context: {
    caller_id_hash: string | null;
    language_hint: string | null;
    background_noise_level: string | null;
    caller_stress_level: string | null;
  };
  triage: {
    priority_score: number | null;
    priority_tier: string | null;
    reason_codes: string[];
  };
  audit: {
    schema_version: string;
    parser_version: string | null;
    scoring_version: string | null;
    processed_at: string | null;
  };
}

export interface ScoreBreakdown {
  reason_code: string;
  weight: number;
  description: string;
}

export interface IncidentPage {
  total: number;
  limit: number;
  offset: number;
  incidents: IncidentRecord[];
}

export interface IngestResponse {
  incident: IncidentRecord;
  score_breakdown: ScoreBreakdown[];
}

export interface ReplayDiff {
  priority_tier_changed: boolean;
  score_delta: number;
  reason_codes_added: string[];
  reason_codes_removed: string[];
}

export interface ReplayResponse {
  original: IncidentRecord;
  replayed: IncidentRecord;
  score_breakdown: ScoreBreakdown[];
  diff: ReplayDiff;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  listIncidents(params: { limit?: number; offset?: number; domain?: string; priority_tier?: string } = {}) {
    const qs = new URLSearchParams();
    if (params.limit)         qs.set('limit', String(params.limit));
    if (params.offset)        qs.set('offset', String(params.offset));
    if (params.domain)        qs.set('domain', params.domain);
    if (params.priority_tier) qs.set('priority_tier', params.priority_tier);
    return request<IncidentPage>(`/incidents?${qs}`);
  },

  getIncident(id: string) {
    return request<IncidentRecord>(`/incidents/${id}`);
  },

  ingest(text: string) {
    return request<IngestResponse>('/ingest', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  replay(id: string) {
    return request<ReplayResponse>(`/replay/${id}`, { method: 'POST' });
  },
};
