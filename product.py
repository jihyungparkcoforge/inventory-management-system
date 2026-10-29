def get_product(connection, product_id):
    row = connection.execute(
        """
        SELECT p.*, s.name AS supplier_name
        FROM products AS p
        JOIN suppliers AS s ON p.supplier_id = s.id
        WHERE p.id = ?
        """,
        (product_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Product not found: {product_id}")

    return row


def add_product(connection, sku, name, category, supplier, price, quantity, reorder):
    row = connection.execute(
        "SELECT id FROM suppliers WHERE name = ?", (supplier,)
    ).fetchone()
    if row is None:
        raise ValueError(f"Supplier not found: {supplier}")

    supplier_id = row["id"]

    sql = "INSERT INTO products (sku, name, category, supplier_id, unit_price, quantity, reorder_level) VALUES (?, ?, ?, ?, ?, ?, ?)"
    cursor = connection.execute(
        sql, (sku, name, category, supplier_id, price, quantity, reorder)
    )
    connection.commit()

    return cursor.lastrowid


def update_product(connection, product_id, update_field, new_value):
    allowed_columns = {"id", "sku", "name", "category", "supplier_id"}

    if update_field not in allowed_columns:
        raise ValueError(f"Invalid search column: {update_field}")

    cursor = connection.execute(
        f"UPDATE products SET {update_field} = ? WHERE id = ?",
        (new_value, product_id),
    )
    connection.commit()
    return cursor.rowcount == 1


def delete_product(connection, product_id):
    rows = connection.execute(
        "SELECT * FROM sale_items WHERE product_id = ?", (product_id,)
    ).fetchone()

    if rows is None:
        cursor = connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
        return cursor.rowcount == 1
    else:
        return False


def search_products(
    connection,
    sku=None,
    name=None,
    supplier_name=None,
    category=None,
    max_price=None,
    in_stock_only=False,
    low_stock_only=False,
):
    conditions = []
    params = []

    if sku is not None:
        conditions.append("p.sku LIKE ?")
        params.append(f"%{sku}%")

    if name is not None:
        conditions.append("p.name LIKE ?")
        params.append(f"%{name}%")

    if supplier_name is not None:
        conditions.append("s.name LIKE ?")
        params.append(f"%{supplier_name}%")

    if category is not None:
        conditions.append("p.category = ?")
        params.append(category)

    if max_price is not None:
        conditions.append("p.unit_price <= ?")
        params.append(max_price)

    if in_stock_only:
        conditions.append("p.quantity > 0")

    if low_stock_only:
        conditions.append("p.quantity <= p.reorder_level")

    sql = """
        SELECT p.*, s.name AS supplier_name
        FROM products AS p
        JOIN suppliers AS s ON p.supplier_id = s.id
    """

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY p.name COLLATE NOCASE, p.id"

    return connection.execute(sql, params).fetchall()
