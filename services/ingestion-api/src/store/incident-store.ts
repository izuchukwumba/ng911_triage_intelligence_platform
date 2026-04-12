import type { IncidentRecord } from '@ng911/incident-schema';
import type { IncidentStore, IncidentQuery, IncidentPage } from './types';

export type { IncidentQuery, IncidentPage };

const store = new Map<string, IncidentRecord>();

export const incidentStore: IncidentStore = {
  save(record: IncidentRecord): void {
    store.set(record.incident_id, record);
  },

  findById(id: string): IncidentRecord | undefined {
    return store.get(id);
  },

  findAll(query: IncidentQuery = {}): IncidentPage {
    const limit = Math.min(query.limit ?? 50, 100);
    const offset = query.offset ?? 0;

    let results = Array.from(store.values()).sort(
      (a, b) =>
        new Date(b.received_at).getTime() - new Date(a.received_at).getTime(),
    );

    if (query.domain) {
      results = results.filter((r) => r.incident.domain === query.domain);
    }

    if (query.priority_tier) {
      results = results.filter((r) => r.triage.priority_tier === query.priority_tier);
    }

    return {
      total: results.length,
      limit,
      offset,
      incidents: results.slice(offset, offset + limit),
    };
  },

  count(): number {
    return store.size;
  },

  clear(): void {
    store.clear();
  },
};
