import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from main import backup_database
from product import add_product, delete_product, search_products, update_product
from seed_db import connect, seed_data


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


@pytest.mark.parametrize(
    "price, quantity",
    [
        (-1, 5),
        (100, -1),
    ],
)
def test_add_product_rejects_negative_values(connection, price, quantity):
    seed_data(connection)

    with pytest.raises(sqlite3.IntegrityError):
        add_product(
            connection,
            "TEST-001",
            "Test product",
            "Tools",
            "Atlas Tools",
            price,
            quantity,
            1,
        )


def test_backup_database(tmp_path):
    source_path = tmp_path / "inventory.db"
    backup_folder = tmp_path / "backups"
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"

    with closing(connect(str(source_path))) as source:
        source.executescript(schema_path.read_text(encoding="utf-8"))
        seed_data(source)
        source.commit()

        backup_path = backup_database(source_path, backup_folder)

        assert backup_path.is_file()

        with closing(connect(str(backup_path))) as backup:
            result = backup.execute("PRAGMA integrity_check").fetchone()
            assert result[0] == "ok"

            tables = (
                "suppliers",
                "products",
                "sales",
                "sale_items",
                "stock_movements",
            )

            for table in tables:
                source_count = source.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]

                backup_count = backup.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]

                assert source_count == backup_count, table


def test_add_new_product(connection):
    seed_data(connection)

    product_id = add_product(
        connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9
    )

    row = connection.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()

    assert row is not None
    assert row["sku"] == "TL-999"


def test_add_product_unknown_supplier(connection):
    seed_data(connection)

    result = add_product(
        connection, "TEST-001", "Test tool", "Tools", "Missing supplier", 100, 5, 1
    )

    assert result is False
    assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 12
    assert connection.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0] == 4


@pytest.mark.parametrize(
    "filters, expected_ids",
    [
        ({"sku": "tl-001"}, [1]),
        ({"name": "cLaW"}, [1]),
        ({"supplier_name": "aTlAs"}, [3, 1, 2]),
    ],
)
def test_search_ignores_case(connection, filters, expected_ids):
    seed_data(connection)

    rows = search_products(connection, **filters)

    assert [row["id"] for row in rows] == expected_ids


@pytest.mark.parametrize(
    "filters, expected_ids",
    [
        ({"category": "Tools"}, [2, 4, 1]),
        ({"max_price": 200}, [2, 3]),
        ({"in_stock_only": True}, [2, 3, 4]),
        ({"low_stock_only": True}, [2, 4, 1]),
        (
            {
                "category": "Tools",
                "max_price": 300,
                "in_stock_only": True,
                "low_stock_only": True,
            },
            [2, 4],
        ),
    ],
)
def test_search_filters(connection, filters, expected_ids):
    with connection:
        connection.execute("INSERT INTO suppliers (id, name) VALUES (1, 'Supplier A')")
        connection.executemany(
            """
            INSERT INTO products
                (id, sku, name, category, supplier_id, unit_price, quantity, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "A", "Zebra", "Tools", 1, 500, 0, 2),
                (2, "B", "alpha", "Tools", 1, 100, 2, 2),
                (3, "C", "Beta", "Plumbing", 1, 200, 5, 1),
                (4, "D", "Gamma", "Tools", 1, 300, 1, 3),
            ],
        )

    rows = search_products(connection, **filters)

    assert [row["id"] for row in rows] == expected_ids


@pytest.mark.parametrize("field", ["sku", "name", "supplier_name", "category"])
def test_search_treats_sql_as_text(connection, field):
    seed_data(connection)
    before = connection.execute("SELECT * FROM products ORDER BY id").fetchall()

    rows = search_products(connection, **{field: "'; DROP TABLE products; --"})

    assert rows == []
    assert connection.execute("SELECT * FROM products ORDER BY id").fetchall() == before


def test_add_dup_sku_new_product(connection):
    seed_data(connection)

    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)
    with pytest.raises(sqlite3.IntegrityError):
        add_product(
            connection, "TL-999", "Test tool2", "Tools", "Atlas Tools", 9999, 99, 9
        )


def test_search_product_by_sku(connection):
    seed_data(connection)
    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)

    row1 = search_products(connection, sku="TL-999")

    assert len(row1) == 1
    assert row1[0]["sku"] == "TL-999"


def test_search_product_by_name(connection):
    seed_data(connection)
    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)

    row2 = search_products(connection, name="Test tool")

    assert row2[0]["sku"] == "TL-999"


def test_search_product_incomplete_sku(connection):
    seed_data(connection)
    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)

    row = search_products(connection, sku="TL-99")
    row_comp = search_products(connection, sku="TL-999")

    assert row == row_comp


def test_search_product_incomplete_name(connection):
    seed_data(connection)
    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)

    row = search_products(connection, name="test t")
    row_comp = search_products(connection, name="Test tool")

    assert row == row_comp


def test_update_product(connection):
    seed_data(connection)

    update = update_product(connection, 1, "name", "CRUD Hammer")
    row = connection.execute("SELECT * FROM products WHERE id = 1").fetchone()

    assert update and row["name"] == "CRUD Hammer"


def test_update_product_price(connection):
    seed_data(connection)

    assert update_product(connection, 1, "unit_price", 2500) is True
    row = connection.execute("SELECT unit_price FROM products WHERE id = 1").fetchone()
    assert row["unit_price"] == 2500


def test_update_missing_product(connection):
    seed_data(connection)
    before = connection.execute("SELECT * FROM products ORDER BY id").fetchall()

    assert update_product(connection, 999, "unit_price", 2500) is False
    assert connection.execute("SELECT * FROM products ORDER BY id").fetchall() == before


def test_update_product_negative_price(connection):
    seed_data(connection)

    with pytest.raises(sqlite3.IntegrityError):
        update_product(connection, 1, "unit_price", -1)
    row = connection.execute("SELECT * FROM products WHERE id = 1").fetchone()

    assert row["unit_price"] != -1


def test_delete_product(connection):
    seed_data(connection)

    delete_saled = delete_product(connection, 1)
    row_block_delete = connection.execute(
        "SELECT * FROM products WHERE id = 1"
    ).fetchone()

    add_product(connection, "TL-999", "Test tool", "Tools", "Atlas Tools", 9999, 99, 9)
    search_row = connection.execute(
        "SELECT * FROM products WHERE sku = 'TL-999'"
    ).fetchone()
    delete_new = delete_product(connection, search_row["id"])
    row_after = connection.execute(
        "SELECT * FROM products WHERE sku = 'TL-999'"
    ).fetchone()

    assert not delete_saled and row_block_delete["name"] != None
    assert delete_new and row_after == None
