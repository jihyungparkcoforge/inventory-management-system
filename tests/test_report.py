from pathlib import Path

import pytest

from report import low_stock, never_sold, sales_by_product, stock_value
from seed_db import connect


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


def test_stock_value_by_supplier(connection):
    connection.executemany(
        "INSERT INTO suppliers (id, name) VALUES (?, ?)",
        [(1, "Supplier A"), (2, "Supplier B"), (3, "Empty Supplier")],
    )
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Product A", "Tools", 1, 100, 2, 1),
            (2, "B", "Product B", "Tools", 1, 200, 3, 1),
            (3, "C", "Product C", "Tools", 2, 300, 4, 1),
        ],
    )

    rows = stock_value(connection)

    # B: 300 * 4 = 1200; A: 100 * 2 + 200 * 3 = 800.
    # List comparison also checks descending stock value order.
    assert [dict(row) for row in rows] == [
        {"supplier_id": 2, "supplier_name": "Supplier B", "stock_value": 1200},
        {"supplier_id": 1, "supplier_name": "Supplier A", "stock_value": 800},
        {"supplier_id": 3, "supplier_name": "Empty Supplier", "stock_value": 0},
    ]


def test_low_stock(connection):
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

    rows = low_stock(connection)

    assert len(rows) == 2
    assert {row["id"]: row["short_level"] for row in rows} == {1: 2, 2: 0}


def test_sales_by_product(connection):
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Product A", "Tools", 1, 9999, 10, 1),
            (2, "B", "Product B", "Tools", 1, 8888, 10, 1),
            (3, "C", "Unsold Product", "Tools", 1, 7777, 10, 1),
        ],
    )
    connection.executemany(
        "INSERT INTO sales (id, sold_at) VALUES (?, ?)",
        [(1, "2026-01-01T10:00:00Z"), (2, "2026-01-02T10:00:00Z")],
    )
    connection.executemany(
        """
        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?)
        """,
        [(1, 1, 2, 100), (2, 1, 1, 150), (1, 2, 1, 500)],
    )

    rows = sales_by_product(connection)

    # A: 3 units, 2 * 100 + 1 * 150 = 350 cents.
    # Revenue must use historical prices, not current product prices.
    assert [dict(row) for row in rows] == [
        {
            "product_id": 2,
            "product_name": "Product B",
            "units_sold": 1,
            "revenue": 500,
        },
        {
            "product_id": 1,
            "product_name": "Product A",
            "units_sold": 3,
            "revenue": 350,
        },
        {
            "product_id": 3,
            "product_name": "Unsold Product",
            "units_sold": 0,
            "revenue": 0,
        },
    ]


def test_never_sold(connection):
    connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
    connection.executemany(
        """
        INSERT INTO products (
            id, sku, name, category, supplier_id,
            unit_price, quantity, reorder_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "A", "Sold Product", "Tools", 1, 100, 10, 1),
            (2, "B", "Unsold B", "Tools", 1, 100, 10, 1),
            (3, "C", "Unsold C", "Tools", 1, 100, 0, 1),
        ],
    )
    connection.execute(
        "INSERT INTO sales (id, sold_at) VALUES (1, '2026-01-01T10:00:00Z')"
    )
    connection.execute(
        """
        INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
        VALUES (1, 1, 2, 100)
        """
    )

    rows = never_sold(connection)

    # Stock quantity does not determine whether a product has been sold.
    assert len(rows) == 2
    assert {row["product_id"]: row["product_name"] for row in rows} == {
        2: "Unsold B",
        3: "Unsold C",
    }
