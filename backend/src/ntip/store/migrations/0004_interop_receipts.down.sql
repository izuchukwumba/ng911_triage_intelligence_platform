-- Rollback of 0004. Destroys stored receipts: only for development and tests.
DROP TABLE IF EXISTS interop_receipts;
