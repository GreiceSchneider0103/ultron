from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "migrations" / "versions"


def _migration_files() -> Iterable[Path]:
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file())


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise RuntimeError("Only sqlite DATABASE_URL is supported by this local runner.")
    raw = database_url[len(prefix) :]
    return (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)


def _ensure_sqlite_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        create table if not exists schema_migrations (
          version text primary key,
          applied_at text not null default (datetime('now'))
        )
        """
    )
    conn.commit()


def _sqlite_applied(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("select version from schema_migrations").fetchall()
    return {r[0] for r in rows}


def _apply_sqlite(conn: sqlite3.Connection, file_path: Path) -> None:
    sql = file_path.read_text(encoding="utf-8")
    sql = (
        sql.replace("public.", "")
        .replace("timestamptz", "text")
        .replace("now()", "CURRENT_TIMESTAMP")
    )
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    for statement in statements:
        try:
            conn.execute(statement)
        except sqlite3.OperationalError as exc:
            # Local dev SQLite may not have full Supabase tables yet (e.g., usage_logs).
            if "no such table" in str(exc).lower():
                continue
            raise
    conn.execute("insert into schema_migrations(version) values (?)", (file_path.stem,))
    conn.commit()


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./ultron.db")
    db_path = _sqlite_path_from_url(database_url)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
        _ensure_sqlite_migrations_table(conn)
        applied = _sqlite_applied(conn)
        for migration in _migration_files():
            if migration.stem in applied:
                continue
            _apply_sqlite(conn, migration)
            print(f"applied: {migration.name}")
    print("migrations: up-to-date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
