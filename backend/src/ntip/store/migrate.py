"""Minimal, reversible SQL migrations.

Migrations are ``NNNN_name.up.sql`` / ``NNNN_name.down.sql`` pairs in
``ntip/store/migrations``. Applied versions are recorded in
``schema_migrations``. Each migration runs in its own transaction.

Usage::

    python -m ntip.store.migrate <database-url>              # apply pending
    python -m ntip.store.migrate <database-url> --down 0000  # roll back to a version
"""

import argparse
from importlib import resources

import psycopg

_DIR = resources.files("ntip.store.migrations")


def available() -> list[str]:
    names = sorted(p.name for p in _DIR.iterdir() if p.name.endswith(".up.sql"))
    return [n.removesuffix(".up.sql") for n in names]


def _sql(name: str, direction: str) -> str:
    return _DIR.joinpath(f"{name}.{direction}.sql").read_text("utf-8")


def applied(conn: psycopg.Connection) -> list[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations"
        " (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    conn.commit()
    return [row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]


def upgrade(url: str) -> list[str]:
    """Apply pending migrations; returns the ones applied."""
    done: list[str] = []
    with psycopg.connect(url) as conn:
        current = set(applied(conn))
        for name in available():
            if name in current:
                continue
            with conn.transaction():
                conn.execute(_sql(name, "up").encode())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (name,))
            done.append(name)
    return done


def downgrade(url: str, target: str) -> list[str]:
    """Roll back every applied migration newer than ``target``."""
    undone: list[str] = []
    with psycopg.connect(url) as conn:
        for name in reversed(applied(conn)):
            if name.split("_", 1)[0] <= target:
                break
            with conn.transaction():
                conn.execute(_sql(name, "down").encode())
                conn.execute("DELETE FROM schema_migrations WHERE version = %s", (name,))
            undone.append(name)
    return undone


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply or roll back ntip migrations.")
    parser.add_argument("url")
    parser.add_argument("--down", metavar="VERSION", help="roll back to this version prefix")
    args = parser.parse_args()
    changed = downgrade(args.url, args.down) if args.down else upgrade(args.url)
    print("\n".join(changed) or "nothing to do")


if __name__ == "__main__":
    main()
