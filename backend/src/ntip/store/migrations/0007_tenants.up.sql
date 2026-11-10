-- Tenants (schema 2.5.0): every incident belongs to one organisation, and
-- replay runs to the tenant that requested them. Rows written before tenants
-- existed belong to the default tenant, which is what their payloads mean.
--
-- Backfilling the new columns is the one update this migration performs, so
-- the append-only triggers are suspended for these statements only.
ALTER TABLE source_events ADD COLUMN tenant_id TEXT;
ALTER TABLE source_events DISABLE TRIGGER source_events_append_only;
UPDATE source_events SET tenant_id = coalesce(payload ->> 'tenant_id', 'default');
ALTER TABLE source_events ENABLE TRIGGER source_events_append_only;
ALTER TABLE source_events ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX source_events_tenant_idx ON source_events (tenant_id, incident_id);

ALTER TABLE replay_runs ADD COLUMN tenant_id TEXT;
ALTER TABLE replay_runs DISABLE TRIGGER replay_runs_append_only;
UPDATE replay_runs SET tenant_id = coalesce(payload ->> 'tenant_id', 'default');
ALTER TABLE replay_runs ENABLE TRIGGER replay_runs_append_only;
ALTER TABLE replay_runs ALTER COLUMN tenant_id SET NOT NULL;
CREATE INDEX replay_runs_tenant_idx ON replay_runs (tenant_id, seq);
