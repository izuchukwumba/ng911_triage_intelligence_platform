import type { IncidentRecord } from '@ng911/incident-schema';

export interface IncidentQuery {
  limit?: number;
  offset?: number;
  domain?: string;
  priority_tier?: string;
}

export interface IncidentPage {
  total: number;
  limit: number;
  offset: number;
  incidents: IncidentRecord[];
}

/**
 * Store interface — all adapters (in-memory, PostgreSQL) must satisfy this.
 * Route handlers depend only on this interface, never on a concrete adapter.
 */
export interface IncidentStore {
  save(record: IncidentRecord): Promise<void> | void;
  findById(id: string): Promise<IncidentRecord | undefined> | IncidentRecord | undefined;
  findAll(query?: IncidentQuery): Promise<IncidentPage> | IncidentPage;
  count(): Promise<number> | number;
  close?(): Promise<void> | void;
}
