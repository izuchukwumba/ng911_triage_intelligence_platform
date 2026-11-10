-- Rollback of 0002. Destroys stored replay runs: only for development and tests.
DROP TABLE IF EXISTS replay_runs;
