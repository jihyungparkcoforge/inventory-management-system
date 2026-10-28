import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[0]
mock_data = {
    "suppliers": {
        "columns": ["id", "name"],
        "rows": [
            (1, "Atlas Tools"),
            (2, "Bright Electrical"),
            (3, "Clearflow Plumbing"),
            (4, "Cornerstone Hardware"),
        ],
    },
    "products": {
        "columns": [
            "id",
            "sku",
            "name",
            "category",
            "supplier_id",
            "unit_price",
            "quantity",
            "reorder_level",
        ],
        "rows": [
            (1, "TL-001", "Claw Hammer", "Tools", 1, 1599, 18, 5),
            (2, "TL-002", "Phillips Screwdriver", "Tools", 1, 699, 25, 8),
            (3, "TL-003", "Adjustable Wrench", "Tools", 1, 1299, 3, 5),
            (4, "EL-001", "LED Bulb", "Electrical", 2, 499, 40, 10),
            (5, "EL-002", "Extension Cord", "Electrical", 2, 1899, 12, 4),
            (6, "EL-003", "Electrical Tape", "Electrical", 2, 299, 30, 10),
            (7, "PL-001", "PVC Elbow", "Plumbing", 3, 249, 4, 4),
            (8, "PL-002", "Thread Seal Tape", "Plumbing", 3, 199, 35, 10),
            (9, "PL-003", "Hose Clamp", "Plumbing", 3, 349, 20, 6),
            (10, "HW-001", "Wood Screws Pack", "Fasteners", 4, 599, 22, 8),
            (11, "HW-002", "Wall Anchors Pack", "Fasteners", 4, 799, 15, 5),
            (12, "HW-003", "Hex Nuts Pack", "Fasteners", 4, 449, 16, 5),
        ],
    },
    "sales": {
        "columns": ["id", "sold_at"],
        "rows": [
            (1, "2026-10-20T09:00:00Z"),
            (2, "2026-10-21T10:15:00Z"),
            (3, "2026-10-22T11:30:00Z"),
            (4, "2026-10-23T14:00:00Z"),
            (5, "2026-10-24T16:45:00Z"),
        ],
    },
    "sale_items": {
        "columns": ["sale_id", "product_id", "quantity", "unit_price"],
        "rows": [
            (1, 1, 1, 1499),
            (1, 2, 2, 699),
            (1, 10, 1, 599),
            (2, 4, 4, 499),
            (2, 5, 1, 1799),
            (3, 7, 3, 249),
            (3, 8, 2, 199),
            (3, 9, 2, 349),
            (4, 3, 1, 1299),
            (4, 6, 2, 299),
            (5, 1, 1, 1599),
            (5, 4, 2, 499),
        ],
    },
}


def connect(db_path: str):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def schema_excutor(connection, schema_path: str):
    SCHEMA_PATH = PROJECT_ROOT / schema_path
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript("BEGIN;\n" + schema + "\nCOMMIT;")


def insert_rows(connection, table, columns, rows):
    column_names = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)

    sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
    connection.executemany(sql, rows)


def seed_data(connection):
    with connection:
        for table, data in mock_data.items():
            insert_rows(
                connection,
                table,
                data["columns"],
                data["rows"],
            )


def main():
    db_path = PROJECT_ROOT / "data" / "inventory.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        con = connect(str(db_path))

        try:
            schema_excutor(con, "schema.sql")
            print("Database tables ready")

            seed_data(con)
            print("Seed data inserted successfully")
        finally:
            con.close()

    except (OSError, sqlite3.Error) as error:
        print(f"Database initialization failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
