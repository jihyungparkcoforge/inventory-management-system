"""Create the initial SQLite tables from app/schema.sql without deleting data."""

import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"


def table_generate() -> Path:
    """
    Initialize tables atomically and return the database's absolute path.
    """
    db_path = PROJECT_ROOT / "data" / "followups.db"

    database_path = Path(db_path).expanduser().resolve()
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        # Foreign keys must be enabled before starting the schema transaction.
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.executescript("BEGIN;\n" + schema + "\nCOMMIT;")

    return database_path


def main():
    try:
        database_path = table_generate()
    except (OSError, sqlite3.Error) as error:
        print(f"Database initialization failed: {error}\n")
        sys.exit(1)
    print(f"Database tables ready: {database_path}")


if __name__ == "__main__":
    main()
