-- Append-only event store (design v1.2, section 9.2).
-- Every table keeps the full JSON document plus a digest of it, and the
-- columns needed for lookups. Rows are never updated or deleted: the trigger
-- at the bottom rejects both, so immutability does not depend on application
-- code behaving.

CREATE TABLE source_events (
    source_event_id TEXT PRIMARY KEY,
    incident_id     TEXT        NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL,
    synthetic       BOOLEAN     NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX source_events_incident_idx ON source_events (incident_id, seq);

CREATE TABLE incident_versions (
    incident_id     TEXT        NOT NULL,
    derived_at      TIMESTAMPTZ NOT NULL,
    schema_version  TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE,
    PRIMARY KEY (incident_id, derived_at)
);

CREATE TABLE assessments (
    assessment_id   TEXT PRIMARY KEY,
    incident_id     TEXT        NOT NULL,
    assessed_at     TIMESTAMPTZ NOT NULL,
    ruleset_version TEXT        NOT NULL,
    status          TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX assessments_incident_idx ON assessments (incident_id, seq);

CREATE TABLE human_reviews (
    review_id       TEXT PRIMARY KEY,
    incident_id     TEXT        NOT NULL,
    assessment_id   TEXT        NOT NULL REFERENCES assessments (assessment_id),
    reviewed_at     TIMESTAMPTZ NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX human_reviews_incident_idx ON human_reviews (incident_id, seq);

CREATE TABLE audit_events (
    event_id        TEXT PRIMARY KEY,
    incident_id     TEXT        NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    event_type      TEXT        NOT NULL,
    correlation_id  TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX audit_events_incident_idx ON audit_events (incident_id, seq);

CREATE TABLE idempotency_claims (
    key             TEXT PRIMARY KEY,
    request_digest  TEXT        NOT NULL,
    incident_id     TEXT        NOT NULL,
    claimed_at      TIMESTAMPTZ NOT NULL,
    payload         JSONB       NOT NULL
);

CREATE FUNCTION ntip_reject_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ntip event store is append-only: % on % is not allowed', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER source_events_append_only BEFORE UPDATE OR DELETE ON source_events
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER incident_versions_append_only BEFORE UPDATE OR DELETE ON incident_versions
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER assessments_append_only BEFORE UPDATE OR DELETE ON assessments
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER human_reviews_append_only BEFORE UPDATE OR DELETE ON human_reviews
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER idempotency_claims_append_only BEFORE UPDATE OR DELETE ON idempotency_claims
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
-- TRUNCATE bypasses row triggers; block it too.
CREATE TRIGGER source_events_no_truncate BEFORE TRUNCATE ON source_events
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER incident_versions_no_truncate BEFORE TRUNCATE ON incident_versions
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER assessments_no_truncate BEFORE TRUNCATE ON assessments
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER human_reviews_no_truncate BEFORE TRUNCATE ON human_reviews
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER idempotency_claims_no_truncate BEFORE TRUNCATE ON idempotency_claims
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
