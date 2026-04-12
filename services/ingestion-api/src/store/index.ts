// ---------------------------------------------------------------------------
// Store selector
//
// Returns the active incident store based on environment.
// Set DATABASE_URL to use PostgreSQL; otherwise falls back to in-memory.
//
// This is the only place that references concrete store implementations.
// All route handlers import from this file, not from a specific adapter.
// ---------------------------------------------------------------------------

import type { IncidentStore } from './types';

let _store: IncidentStore | null = null;

export function getStore(): IncidentStore {
  if (_store) return _store;

  const dbUrl = process.env['DATABASE_URL'];
  if (dbUrl) {
    // Lazy-load the PostgreSQL adapter so the pg package is not required
    // in environments that don't have it installed.
    const { PostgresIncidentStore } = require('./postgres-store') as typeof import('./postgres-store');
    _store = new PostgresIncidentStore(dbUrl);
    console.log('[store] Using PostgreSQL incident store');
  } else {
    const { incidentStore } = require('./incident-store') as typeof import('./incident-store');
    _store = incidentStore;
    console.log('[store] Using in-memory incident store (set DATABASE_URL to use PostgreSQL)');
  }

  return _store;
}

export type { IncidentStore, IncidentQuery, IncidentPage } from './types';
