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

    adjust(connection, id=1, amount=-4)
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

    result = record_sales(
        connection, [(1, 1), (2, 5), (3, 2)], occurred_at="2026-01-01T12:00:00+00:00"
    )
    assert result is True

    list_after = connection.execute(
        "SELECT quantity FROM products ORDER BY id"
    ).fetchall()
    assert [row["quantity"] for row in list_after] == [2, 0, 6]

    sales_before = connection.execute("SELECT * FROM sales ORDER BY id").fetchall()
    items_before = connection.execute(
        "SELECT * FROM sale_items ORDER BY sale_id, product_id"
    ).fetchall()
    movements_before = connection.execute(
        "SELECT * FROM stock_movements ORDER BY id"
    ).fetchall()

    assert len(sales_before) == 1
    assert sales_before[0]["sold_at"] == "2026-01-01T12:00:00+00:00"
    assert len(items_before) == 3
    assert len(movements_before) == 3
    for row in items_before:
        assert row["sale_id"] == sales_before[0]["id"]
        assert row["unit_price"] == 100
    assert [row["quantity"] for row in items_before] == [1, 5, 2]
    assert [row["quantity_change"] for row in movements_before] == [-1, -5, -2]
    for row in movements_before:
        assert row["reason"] == "sale"
        assert row["occurred_at"] == sales_before[0]["sold_at"]

    # The first item succeeds, but the second item has no stock left.
    result = record_sales(connection, [(1, 1), (2, 5), (3, 10)])
    assert result is False
    list_after2 = connection.execute(
        "SELECT quantity FROM products ORDER BY id"
    ).fetchall()
    assert list_after == list_after2

    # Previously committed sales and movements must remain unchanged.
    assert (
        connection.execute("SELECT * FROM sales ORDER BY id").fetchall() == sales_before
    )
    assert (
        connection.execute(
            "SELECT * FROM sale_items ORDER BY sale_id, product_id"
        ).fetchall()
        == items_before
    )
    assert (
        connection.execute("SELECT * FROM stock_movements ORDER BY id").fetchall()
        == movements_before
    )


def prepare_sale_products(connection):
    """Insert two products with known stock and commit the test data."""
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Product A", "Tools", 1, 100, 3, 5),
            (2, "B", "Product B", "Tools", 1, 200, 5, 5),
        ],
    )
    connection.commit()


def test_sale_rolls_back_when_stock_is_insufficient(connection):
    prepare_sale_products(connection)

    result = record_sales(connection, [(1, 1), (2, 999)])

    assert result is False
    rows = connection.execute("SELECT quantity FROM products ORDER BY id").fetchall()
    assert [row["quantity"] for row in rows] == [3, 5]
    assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
    assert connection.in_transaction is False


def test_sale_rolls_back_when_product_does_not_exist(connection):
    prepare_sale_products(connection)

    result = record_sales(connection, [(1, 1), (999, 1)])

    assert result is False
    rows = connection.execute("SELECT quantity FROM products ORDER BY id").fetchall()
    assert [row["quantity"] for row in rows] == [3, 5]
    assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
    assert connection.in_transaction is False


def test_sale_rejects_duplicate_products(connection):
    prepare_sale_products(connection)

    result = record_sales(connection, [(1, 1), (1, 1)])

    assert result is False
    rows = connection.execute("SELECT quantity FROM products ORDER BY id").fetchall()
    assert [row["quantity"] for row in rows] == [3, 5]
    assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0


def test_sale_rejects_zero_and_negative_quantity(connection):
    prepare_sale_products(connection)

    for quantity in [0, -1]:
        result = record_sales(connection, [(1, quantity)])

        assert result is False
        rows = connection.execute(
            "SELECT quantity FROM products ORDER BY id"
        ).fetchall()
        assert [row["quantity"] for row in rows] == [3, 5]
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
        assert (
            connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0]
            == 0
        )


def test_sale_rejects_empty_items(connection):
    prepare_sale_products(connection)

    result = record_sales(connection, [])

    assert result is False
    rows = connection.execute("SELECT quantity FROM products ORDER BY id").fetchall()
    assert [row["quantity"] for row in rows] == [3, 5]
    assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM sale_items").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0] == 0
