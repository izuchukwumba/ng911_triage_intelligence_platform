-- A restricted role for the application (design v1.2 section 9; threat model:
-- audit tampering). The API should connect as a login role that is a member of
-- ntip_app, never as the owner of the tables:
--
--   * it may read and append, and nothing else: no UPDATE, DELETE or TRUNCATE
--     even if the append-only triggers were removed;
--   * it owns nothing, so it cannot drop or disable those triggers;
--   * it cannot read or change schema_migrations.
--
-- Roles belong to the whole PostgreSQL cluster. ntip_app is created only if it
-- does not exist, so a DBA may create it beforehand and the migrating user then
-- needs no CREATEROLE privilege. Every later migration that adds a table must
-- grant ntip_app SELECT, INSERT on it (a test checks this).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ntip_app') THEN
        CREATE ROLE ntip_app NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO ntip_app;
GRANT SELECT, INSERT ON
    source_events, incident_versions, assessments, human_reviews, audit_events,
    idempotency_claims, replay_runs, model_outputs, interop_receipts
TO ntip_app;
-- BIGSERIAL seq columns draw from these on INSERT.
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO ntip_app;
