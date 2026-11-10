-- Identify incident versions by number instead of derivation time.
-- Version n is the interpretation of the incident's first n source events.
-- Concurrent derivations could share a timestamp and collide on the old key;
-- with optimistic concurrency control, at most one version n can be written.
--
-- Backfilling the new column is the one update this migration performs, so
-- the append-only trigger is suspended for this statement only.
ALTER TABLE incident_versions ADD COLUMN version INTEGER;

ALTER TABLE incident_versions DISABLE TRIGGER incident_versions_append_only;
UPDATE incident_versions SET version = jsonb_array_length(payload -> 'source_event_ids');
ALTER TABLE incident_versions ENABLE TRIGGER incident_versions_append_only;

ALTER TABLE incident_versions ALTER COLUMN version SET NOT NULL;
ALTER TABLE incident_versions DROP CONSTRAINT incident_versions_pkey;
ALTER TABLE incident_versions ADD PRIMARY KEY (incident_id, version);
