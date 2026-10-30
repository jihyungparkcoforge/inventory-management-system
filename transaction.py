from datetime import UTC, datetime


def restock(connection, id, amount, occurred_at=None):
    """Increase stock and log the movement in one transaction."""
    if type(amount) is not int or amount <= 0:
        return False

    occurred_at = (
        occurred_at if occurred_at is not None else datetime.now(UTC).isoformat()
    )
    with connection:
        cursor = connection.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ?", (amount, id)
        )
        if cursor.rowcount == 0:
            return False
        connection.execute(
            """
            INSERT INTO stock_movements (product_id, quantity_change, reason, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (id, amount, "restock", occurred_at),
        )
    return True


def adjust(connection, id, amount, occurred_at=None):
    """Apply a signed stock adjustment and log it atomically; refuse negative stock."""
    if type(amount) is not int:
        return False

    occurred_at = (
        occurred_at if occurred_at is not None else datetime.now(UTC).isoformat()
    )
    with connection:
        cursor = connection.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ? AND quantity + ? >= 0",
            (amount, id, amount),
        )
        if cursor.rowcount == 0:
            return False
        connection.execute(
            """
            INSERT INTO stock_movements (product_id, quantity_change, reason, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (id, amount, "adjustment", occurred_at),
        )
    return True


def record_sales(connection, products_quantities, occurred_at=None):
    """Save one sale, its price snapshots and stock movements atomically.

    Return False for invalid items or insufficient stock. Database errors propagate
    after rollback so the caller can report them. All records share one timestamp.
    """
    try:
        items = list(products_quantities)
        if not items:
            return False
        seen_ids = set()
        for product_id, quantity in items:
            if (
                type(product_id) is not int
                or product_id <= 0
                or type(quantity) is not int
                or quantity <= 0
                or product_id in seen_ids
            ):
                return False
            seen_ids.add(product_id)
    except (TypeError, ValueError):
        return False

    occurred_at = (
        occurred_at if occurred_at is not None else datetime.now(UTC).isoformat()
    )
    try:
        with connection:
            sale_cursor = connection.execute(
                "INSERT INTO sales (sold_at) VALUES (?)", (occurred_at,)
            )
            sale_id = sale_cursor.lastrowid

            for product_id, quantity in items:
                cursor = connection.execute(
                    "UPDATE products SET quantity = quantity - ? WHERE id = ? AND quantity >= ?",
                    (quantity, product_id, quantity),
                )
                if cursor.rowcount == 0:
                    # Raising here rolls back the sale and all earlier items.
                    raise ValueError("Unknown product or insufficient stock.")

                price = connection.execute(
                    "SELECT unit_price FROM products WHERE id = ?", (product_id,)
                ).fetchone()["unit_price"]
                connection.execute(
                    """
                    INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sale_id, product_id, quantity, price),
                )
                connection.execute(
                    """
                    INSERT INTO stock_movements (
                        product_id, quantity_change, reason, occurred_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (product_id, -quantity, "sale", occurred_at),
                )
    except ValueError:
        return False

    return True
