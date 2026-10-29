from pathlib import Path

from product import add_product, delete_product, search_products, update_product
from seed_db import connect, seed_data


def test_add_new_product():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    connection = connect(":memory:")

    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        seed_data(connection)

        add_product(connection, "TL-999", "Test tool","Tools", "Atlas Tools", 9999, 99, 9)

        row = connection.execute("SELECT * FROM products WHERE name = 'Test tool'").fetchone()

        assert row["sku"] == "TL-999"
    finally:
        connection.close()


def test_search_product():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    connection = connect(":memory:")

    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        seed_data(connection)
        add_product(connection, "TL-999", "Test tool","Tools", "Atlas Tools", 9999, 99, 9)

        row1 = search_products(connection, sku="TL-999")
        row2 = search_products(connection, name="Test tool")
        row3 = search_products(connection, sku="TL-999", max_price=999)

        assert len(row1) == 1
        assert row1[0]["sku"] == "TL-999"

        assert {row["id"] for row in row1} == {
            row["id"] for row in row2
        }

        assert row3 == []
    finally:
        connection.close()

def test_search_product_incomplete_argument():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    connection = connect(":memory:")

    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        seed_data(connection)
        add_product(connection, "TL-999", "Test tool","Tools", "Atlas Tools", 9999, 99, 9)

        row1 = search_products(connection, sku="TL-99")
        row1_comp = search_products(connection, sku="TL-999")

        row2 = search_products(connection, name="test t")
        row2_comp = search_products(connection, name="Test tool")

        row3 = search_products(connection, supplier_name="atl")
        row3_comp = search_products(connection, supplier_name="Atlas Tools")


        assert row1 == row1_comp
        assert row2 == row2_comp
        assert row3 == row3_comp
    finally:
        connection.close()

def test_update_product():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    connection = connect(":memory:")

    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        seed_data(connection)

        update = update_product(connection, 1, "name", "CRUD Hammer")
        row = connection.execute("SELECT * FROM products WHERE id = 1").fetchone()

        assert update and row["name"] == "CRUD Hammer"
    finally:
        connection.close()


def test_delete_product():
    schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
    connection = connect(":memory:")

    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))

        seed_data(connection)

        delete_saled = delete_product(connection, 1)
        row_block_delete = connection.execute("SELECT * FROM products WHERE id = 1").fetchone()

        add_product(connection, "TL-999", "Test tool","Tools", "Atlas Tools", 9999, 99, 9)
        search_row = connection.execute("SELECT * FROM products WHERE sku = 'TL-999'").fetchone()
        delete_new = delete_product(connection, search_row["id"])
        row_after = connection.execute("SELECT * FROM products WHERE sku = 'TL-999'").fetchone()


        assert not delete_saled and row_block_delete["name"] != None
        assert delete_new and row_after == None
    finally:
        connection.close()
