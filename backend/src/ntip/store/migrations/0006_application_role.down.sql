-- Rollback of 0006: withdraw this database's grants. The role itself is
-- cluster-wide and may be used by other databases, so it is left in place.
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM ntip_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM ntip_app;
REVOKE USAGE ON SCHEMA public FROM ntip_app;
