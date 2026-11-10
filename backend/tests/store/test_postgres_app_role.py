"""The restricted application role can read and append, and nothing else.

The contract tests also run as this role (see the ``store`` fixture), which
shows it is sufficient for everything the store does.
"""

import psycopg
import pytest

from ntip.store.migrate import upgrade
from ntip.store.postgres import APP_ROLE, EVENT_TABLES


@pytest.mark.parametrize("table", EVENT_TABLES)
@pytest.mark.parametrize(
    "statement",
    ["UPDATE {t} SET payload = payload", "DELETE FROM {t}", "TRUNCATE {t}",
     "ALTER TABLE {t} DISABLE TRIGGER ALL", "DROP TABLE {t}"],
)  # fmt: skip
def test_cannot_change_or_bypass_the_record(app_role_url: str, table: str, statement: str) -> None:
    # Refused by privileges, before any append-only trigger is consulted.
    with (
        psycopg.connect(app_role_url) as conn,
        pytest.raises(psycopg.errors.InsufficientPrivilege, match=r"permission denied|owner"),
    ):
        conn.execute(statement.format(t=table))


def test_cannot_touch_the_migration_history(app_role_url: str) -> None:
    with (
        psycopg.connect(app_role_url) as conn,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        conn.execute("SELECT * FROM schema_migrations")


PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


def test_every_table_grants_the_role_exactly_select_and_insert(postgres_url: str) -> None:
    """Catches a future migration that adds a table without granting it."""
    upgrade(postgres_url)
    with psycopg.connect(postgres_url) as conn:
        rows = conn.execute(
            "SELECT t.tablename, p.name FROM pg_tables t CROSS JOIN unnest(%s::text[]) p(name)"
            " WHERE t.schemaname = 'public' AND has_table_privilege(%s, t.tablename, p.name)",
            (list(PRIVILEGES), APP_ROLE),
        ).fetchall()
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        granted: dict[str, set[str]] = {table: set() for (table,) in tables}
    for table, privilege in rows:
        granted[table].add(privilege)
    expected = {t: {"SELECT", "INSERT"} for t in EVENT_TABLES} | {
        "schema_migrations": set(),
        "erasures": {"SELECT"},  # visible, never written by the application
    }
    assert granted == expected
