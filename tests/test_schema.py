import sqlite3
from contextlib import closing
from pathlib import Path


def test_schema_creates_required_tables():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_sql)

        rows = connection.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'"
        ).fetchall()
        actual_tables = {row[0] for row in rows}

    required_tables = {
        "suppliers",
        "products",
        "sales",
        "sale_items",
        "stock_movements",
    }
    missing_tables = required_tables - actual_tables
    assert not missing_tables, f"Missing tables: {sorted(missing_tables)}"
