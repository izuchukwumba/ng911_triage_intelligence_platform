-- Rollback of 0005: restore the (incident_id, derived_at) key.
ALTER TABLE incident_versions DROP CONSTRAINT incident_versions_pkey;
ALTER TABLE incident_versions ADD PRIMARY KEY (incident_id, derived_at);
ALTER TABLE incident_versions DROP COLUMN version;
