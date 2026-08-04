from __future__ import annotations

import os
from pathlib import Path

import psycopg


def main() -> None:
    repository = Path(__file__).resolve().parents[2]
    migration_directory = repository / "backend" / "src" / "main" / "resources" / "db" / "migration"
    database_url = os.environ["ANALYTICS_DATABASE_URL"]
    migrations = sorted(migration_directory.glob("V*__*.sql"), key=_migration_version)

    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        for migration in migrations:
            cursor.execute(migration.read_text(encoding="utf-8"))
            print(f"Applied {migration.name}")


def _migration_version(path: Path) -> int:
    return int(path.name.split("__", maxsplit=1)[0][1:])


if __name__ == "__main__":
    main()
