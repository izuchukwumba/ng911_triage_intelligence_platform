-- Rollback of 0008: drop the tombstones and restore the strict trigger.
DROP TABLE erasures;
DROP FUNCTION ntip_reject_any_mutation();
CREATE OR REPLACE FUNCTION ntip_reject_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'ntip event store is append-only: % on % is not allowed', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
