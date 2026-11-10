-- Rollback of 0007. Payloads keep their tenant_id; only the columns go.
DROP INDEX replay_runs_tenant_idx;
ALTER TABLE replay_runs DROP COLUMN tenant_id;
DROP INDEX source_events_tenant_idx;
ALTER TABLE source_events DROP COLUMN tenant_id;
