-- Rollback of 0001. Destroys all stored events: only for development and tests.
DROP TABLE IF EXISTS idempotency_claims;
DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS human_reviews;
DROP TABLE IF EXISTS assessments;
DROP TABLE IF EXISTS incident_versions;
DROP TABLE IF EXISTS source_events;
DROP FUNCTION IF EXISTS ntip_reject_mutation();
