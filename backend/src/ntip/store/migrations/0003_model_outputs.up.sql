-- Recorded model calls (design v1.2, section 3A.9). Append-only.
CREATE TABLE model_outputs (
    output_id       TEXT PRIMARY KEY,
    incident_id     TEXT        NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL,
    mode            TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX model_outputs_incident_idx ON model_outputs (incident_id, seq);

CREATE TRIGGER model_outputs_append_only BEFORE UPDATE OR DELETE ON model_outputs
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER model_outputs_no_truncate BEFORE TRUNCATE ON model_outputs
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
