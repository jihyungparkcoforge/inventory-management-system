from pathlib import Path

import pytest

from seed_db import connect
from transaction import adjust, record_sales, restock


@pytest.fixture
def connection():
    """Give each test a fresh database with tables but no seed data."""
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    db = connect(":memory:")
    try:
        db.executescript(schema_path.read_text(encoding="utf-8"))
        yield db
    finally:
        db.close()


def test_restock(connection):
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Below level", "Tools", 1, 100, 3, 5),
            (2, "B", "At level", "Tools", 1, 100, 5, 5),
            (3, "C", "Above level", "Tools", 1, 100, 8, 5),
        ],
    )
    quantity_before = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]
    restock(connection, id=1, amount=2)
    quantity_after = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]

    assert quantity_after == quantity_before + 2

    restock(connection, id=1, amount=-1)
    quantity_after2 = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]

    assert quantity_after2 == quantity_after


def test_adjust(connection):
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Below level", "Tools", 1, 100, 3, 5),
            (2, "B", "At level", "Tools", 1, 100, 5, 5),
            (3, "C", "Above level", "Tools", 1, 100, 8, 5),
        ],
    )
    quantity_before = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]
    adjust(connection, id=1, amount=-2)
    quantity_after = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]

    assert quantity_after == quantity_before - 2

    restock(connection, id=1, amount=-4)
    quantity_after2 = connection.execute(
        "SELECT quantity FROM products WHERE id = 1"
    ).fetchone()["quantity"]

    assert quantity_after2 == quantity_after


def test_record_sales(connection):
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Below level", "Tools", 1, 100, 3, 5),
            (2, "B", "At level", "Tools", 1, 100, 5, 5),
            (3, "C", "Above level", "Tools", 1, 100, 8, 5),
        ],
    )
    connection.commit()

    list_before = connection.execute(
        "SELECT quantity FROM products ORDER BY quantity"
    ).fetchall()

    record_sales(connection, [(1, 1), (2, 5), (3, 2)])

    list_after = connection.execute(
        "SELECT quantity FROM products ORDER BY quantity"
    ).fetchall()

    assert list_before != list_after

    record_sales(connection, [(1, 1), (2, 5), (3, 10)])

    list_after2 = connection.execute(
        "SELECT quantity FROM products ORDER BY quantity"
    ).fetchall()

    assert list_after == list_after2
