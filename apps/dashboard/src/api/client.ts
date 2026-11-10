// Typed client for the research backend's /v1 API.
// All types come from src/api/schema.ts, generated from backend/openapi.json
// (`npm run gen:api`); do not hand-write response shapes here.

import type { components } from './schema';

type Schemas = components['schemas'];

export type IncidentSummary = Schemas['IncidentSummaryOut'];
export type IncidentPage = Schemas['IncidentPage'];
export type IncidentDetail = Schemas['IncidentDetail'];
export type Incident = Schemas['Incident'];
export type Observation = Schemas['Observation'];
export type LocationCandidate = Schemas['LocationCandidate'];
export type Assessment = Schemas['Assessment'];
export type RuleFiring = Schemas['RuleFiring'];
export type HumanReview = Schemas['HumanReview'];
export type AuditEvent = Schemas['AuditEvent'];
export type IngestOut = Schemas['IngestOut'];
export type ReviewIn = Schemas['ReviewIn'];
export type Priority = Schemas['AdvisoryPriority'];
export type ReviewAction = Schemas['ReviewAction'];
export type EvaluationReport = Schemas['EvaluationReport'];
export type DatasetName = Schemas['DatasetName'];
export type ReportSplit = Schemas['ReportSplit'];

// Same-origin in development (Vite proxies /v1 and /health to the backend).
const BASE = import.meta.env.VITE_API_BASE ?? '';

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly correlationId: string | null,
  ) {
    super(message);
  }
}

// The API token lives only for this browser tab (sessionStorage), never in
// localStorage or the bundle.
const TOKEN_KEY = 'ntip.apiToken';

export function getToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? '';
  } catch {
    return '';
  }
}

export function setToken(token: string): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable: the token simply is not remembered
  }
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as
      | { error?: { code?: string; message?: string } }
      | null;
    throw new ApiError(
      res.status,
      body?.error?.code ?? 'http_error',
      body?.error?.message ?? res.statusText,
      res.headers.get('X-Correlation-ID'),
    );
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await send(path, init)).json()) as T;
}

function post<T>(path: string, body: unknown, headers?: Record<string, string>) {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body), headers });
}

export const api = {
  listIncidents(limit = 100, offset = 0) {
    return request<IncidentPage>(`/v1/incidents?limit=${limit}&offset=${offset}`);
  },
  getIncident(id: string) {
    return request<IncidentDetail>(`/v1/incidents/${encodeURIComponent(id)}`);
  },
  getEvents(id: string) {
    return request<Schemas['AuditTrail']>(`/v1/incidents/${encodeURIComponent(id)}/events`);
  },
  ingest(text: string) {
    // A fresh key per submission makes accidental double-submits harmless.
    return post<IngestOut>(
      '/v1/incidents',
      { text, synthetic: true },
      { 'Idempotency-Key': crypto.randomUUID() },
    );
  },
  addMessage(id: string, text: string) {
    return post<IngestOut>(
      `/v1/incidents/${encodeURIComponent(id)}/messages`,
      { text, synthetic: true },
      { 'Idempotency-Key': crypto.randomUUID() },
    );
  },
  review(id: string, body: ReviewIn) {
    return post<HumanReview>(`/v1/incidents/${encodeURIComponent(id)}/reviews`, body);
  },
  rulesets() {
    return request<Schemas['RulesetOut'][]>('/v1/rulesets');
  },
  replayRuns() {
    return request<Schemas['ReplayRun'][]>('/v1/replay-runs?limit=1');
  },
  replay(body: Schemas['ReplayIn']) {
    return post<Schemas['ReplayRun']>('/v1/replay-runs', body);
  },
  evaluationReport(dataset: DatasetName, splits: ReportSplit[]) {
    return request<EvaluationReport>(`/v1/evaluation/report?${evaluationQuery(dataset, splits)}`);
  },
  async evaluationMarkdown(dataset: DatasetName, splits: ReportSplit[]) {
    return (await send(`/v1/evaluation/report.md?${evaluationQuery(dataset, splits)}`)).text();
  },
  ready() {
    return request<{ status: string }>('/health/ready');
  },
};

function evaluationQuery(dataset: DatasetName, splits: ReportSplit[]): string {
  const query = new URLSearchParams({ dataset });
  for (const split of splits) query.append('split', split);
  return query.toString();
}
