-- Receipts for external (EIDO) submissions, design v1.2 section 3B.3. Append-only.
CREATE TABLE interop_receipts (
    receipt_id      TEXT PRIMARY KEY,
    tenant_id       TEXT        NOT NULL,
    source_event_id TEXT,
    received_at     TIMESTAMPTZ NOT NULL,
    status          TEXT        NOT NULL,
    payload         JSONB       NOT NULL,
    payload_digest  TEXT        NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX interop_receipts_source_idx ON interop_receipts (tenant_id, source_event_id, seq);

CREATE TRIGGER interop_receipts_append_only BEFORE UPDATE OR DELETE ON interop_receipts
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER interop_receipts_no_truncate BEFORE TRUNCATE ON interop_receipts
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
