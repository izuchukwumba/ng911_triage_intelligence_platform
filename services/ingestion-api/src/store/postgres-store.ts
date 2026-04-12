import { Pool } from 'pg';
import type { IncidentRecord } from '@ng911/incident-schema';
import type { IncidentStore, IncidentQuery, IncidentPage } from './types';

// ---------------------------------------------------------------------------
// PostgreSQL Incident Store
//
// Uses a single JSONB column to store the full incident record, with
// extracted scalar columns for efficient filtering and sorting.
//
// Schema (auto-created on first connect):
//
//   CREATE TABLE incidents (
//     incident_id   UUID        PRIMARY KEY,
//     received_at   TIMESTAMPTZ NOT NULL,
//     domain        TEXT        NOT NULL,
//     priority_tier TEXT,
//     priority_score NUMERIC(5,3),
//     record        JSONB       NOT NULL,
//     created_at    TIMESTAMPTZ DEFAULT NOW()
//   );
// ---------------------------------------------------------------------------

const CREATE_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS incidents (
    incident_id    UUID         PRIMARY KEY,
    received_at    TIMESTAMPTZ  NOT NULL,
    domain         TEXT         NOT NULL,
    priority_tier  TEXT,
    priority_score NUMERIC(5,3),
    record         JSONB        NOT NULL,
    created_at     TIMESTAMPTZ  DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_incidents_received_at   ON incidents (received_at DESC);
  CREATE INDEX IF NOT EXISTS idx_incidents_domain        ON incidents (domain);
  CREATE INDEX IF NOT EXISTS idx_incidents_priority_tier ON incidents (priority_tier);
`;

export class PostgresIncidentStore implements IncidentStore {
  private pool: Pool;
  private ready: Promise<void>;

  constructor(connectionString: string) {
    this.pool = new Pool({ connectionString });
    this.ready = this.initialise();
  }

  private async initialise(): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query(CREATE_TABLE_SQL);
    } finally {
      client.release();
    }
  }

  async save(record: IncidentRecord): Promise<void> {
    await this.ready;
    await this.pool.query(
      `INSERT INTO incidents (incident_id, received_at, domain, priority_tier, priority_score, record)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (incident_id) DO UPDATE
         SET priority_tier  = EXCLUDED.priority_tier,
             priority_score = EXCLUDED.priority_score,
             record         = EXCLUDED.record`,
      [
        record.incident_id,
        record.received_at,
        record.incident.domain,
        record.triage.priority_tier,
        record.triage.priority_score,
        JSON.stringify(record),
      ],
    );
  }

  async findById(id: string): Promise<IncidentRecord | undefined> {
    await this.ready;
    const result = await this.pool.query(
      'SELECT record FROM incidents WHERE incident_id = $1',
      [id],
    );
    if (result.rows.length === 0) return undefined;
    return result.rows[0].record as IncidentRecord;
  }

  async findAll(query: IncidentQuery = {}): Promise<IncidentPage> {
    await this.ready;
    const limit = Math.min(query.limit ?? 50, 500);
    const offset = query.offset ?? 0;
    const conditions: string[] = [];
    const params: unknown[] = [];

    if (query.domain) {
      params.push(query.domain);
      conditions.push(`domain = $${params.length}`);
    }

    if (query.priority_tier) {
      params.push(query.priority_tier);
      conditions.push(`priority_tier = $${params.length}`);
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    const countResult = await this.pool.query(
      `SELECT COUNT(*)::int AS total FROM incidents ${where}`,
      params,
    );
    const total: number = countResult.rows[0].total;

    params.push(limit, offset);
    const dataResult = await this.pool.query(
      `SELECT record FROM incidents ${where}
       ORDER BY received_at DESC
       LIMIT $${params.length - 1} OFFSET $${params.length}`,
      params,
    );

    return {
      total,
      limit,
      offset,
      incidents: dataResult.rows.map((r) => r.record as IncidentRecord),
    };
  }

  async count(): Promise<number> {
    await this.ready;
    const result = await this.pool.query('SELECT COUNT(*)::int AS n FROM incidents');
    return result.rows[0].n as number;
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}
