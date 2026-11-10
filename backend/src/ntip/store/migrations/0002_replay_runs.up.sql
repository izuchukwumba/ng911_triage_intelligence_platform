-- Replay runs (design v1.2, section 10). Append-only like every other table.
CREATE TABLE replay_runs (
    run_id            TEXT PRIMARY KEY,
    created_at        TIMESTAMPTZ NOT NULL,
    candidate_ruleset TEXT,
    payload           JSONB       NOT NULL,
    payload_digest    TEXT        NOT NULL,
    seq               BIGSERIAL   NOT NULL UNIQUE
);

CREATE TRIGGER replay_runs_append_only BEFORE UPDATE OR DELETE ON replay_runs
    FOR EACH ROW EXECUTE FUNCTION ntip_reject_mutation();
CREATE TRIGGER replay_runs_no_truncate BEFORE TRUNCATE ON replay_runs
    FOR EACH STATEMENT EXECUTE FUNCTION ntip_reject_mutation();
