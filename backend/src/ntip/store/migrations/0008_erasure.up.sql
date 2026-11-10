-- Lawful erasure (design v1.2, section 9.3: audit retention must not override
-- privacy and deletion requirements).
--
-- The event store stays append-only for the application: ntip_app has no
-- DELETE privilege, and UPDATE and TRUNCATE remain refused for everyone. Only
-- the erasure procedure (python -m ntip.store.retention, run as the table
-- owner) may delete, and only inside a transaction that has set the
-- transaction-local setting ntip.erasure_id. Every erasure leaves a tombstone
-- in the append-only erasures table, which records what was erased, when, by
-- whom and why, but no content.
CREATE OR REPLACE FUNCTION ntip_reject_mutation() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND coalesce(current_setting('ntip.erasure_id', true), '') <> '' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'ntip event store is append-only: % on % is not allowed', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION ntip_reject_any_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ntip erasure records are permanent: % on % is not allowed', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TABLE erasures (
    erasure_id      TEXT        PRIMARY KEY,
    -- "incident": one incident and everything derived from it;
    -- "receipt": an EIDO receipt that never became an incident.
    scope           TEXT        NOT NULL CHECK (scope IN ('incident', 'receipt')),
    subject_id      TEXT        NOT NULL,
    tenant_id       TEXT        NOT NULL,
    erased_at       TIMESTAMPTZ NOT NULL,
    requested_by    TEXT        NOT NULL,
    reason          TEXT        NOT NULL,
    rows_deleted    JSONB       NOT NULL,
    seq             BIGSERIAL   NOT NULL UNIQUE
);
CREATE INDEX erasures_subject_idx ON erasures (subject_id);

CREATE TRIGGER erasures_append_only BEFORE UPDATE OR DELETE ON erasures
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_any_mutation();
CREATE TRIGGER erasures_no_truncate BEFORE TRUNCATE ON erasures
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_any_mutation();

-- The application may see that something was erased, never write or remove it.
GRANT SELECT ON erasures TO ntip_app;
