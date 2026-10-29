from time import time


def restock(connection, id, amount):
    """
    Restock. Increase a product’s stock by a positive amount and log a restock movement.
    An amount of zero or less is refused.
    """
    if amount > 0:
        cursor = connection.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ?", (amount, id)
        )

        connection.execute(
            """
            INSERT INTO stock_movements (product_id, quantity_change, reason, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (id, amount, "restock", str(time)),
        )
        connection.commit()
        return cursor.lastrowid
    else:
        return False


def adjust(connection, id, amount):
    """
    Adjust. Change stock by a signed amount for damage or a recount, and log an adjustment movement.
    An adjustment that would make stock negative fails and changes nothing.
    """
    cursor = connection.execute(
        "UPDATE products SET quantity = quantity + ? WHERE id = ? AND quantity + ? >= 0",
        (amount, id, amount),
    )
    if cursor.rowcount > 0:
        connection.execute(
            """
            INSERT INTO stock_movements (product_id, quantity_change, reason, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (id, amount, "adjustment", str(time)),
        )
        connection.commit()

    return cursor.lastrowid


def record_sales(connection, products_quantities):
    """
    Record a sale. Take a list of product and quantity pairs.
    Create the sale, add a line for each product at the product’s current price, reduce each product’s stock, and log a sale movement for each line.
    If any line fails (not enough stock, an unknown product, or the same product twice), the whole sale is undone.
    """
    for product, quantity in products_quantities:
        cursor = connection.execute(
            "UPDATE products SET quantity = quantity - ? WHERE id = ? AND quantity >= ?",
            (quantity, product, quantity),
        )
        connection.execute(
            """
            INSERT INTO stock_movements (product_id, quantity_change, reason, occurred_at)
            VALUES (?, ?, ?, ?)
            """,
            (product, quantity, "sale", str(time)),
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return False

    connection.commit()
    return True
