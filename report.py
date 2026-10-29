def stock_value(connection):
    """
    Stock value by supplier: the supplier name and the total value of its stock (price times quantity), highest first.
    """
    rows = connection.execute(
        """
        SELECT s.id AS supplier_id,
        s.name AS supplier_name,
        COALESCE(SUM(p.quantity * p.unit_price), 0) AS stock_value
        FROM suppliers AS s
        LEFT JOIN products AS p ON s.id = p.supplier_id
        GROUP BY s.id
        ORDER BY stock_value DESC, s.id
        """
    ).fetchall()

    return rows


def low_stock(connection):
    """
    Low stock: every product at or below its reorder level, with how many units short of the level it is.
    """
    rows = connection.execute(
        """
        SELECT *, COALESCE((reorder_level - quantity), 0) AS short_level
        FROM products
        WHERE quantity <= reorder_level
        """
    ).fetchall()

    return rows


def sales_by_product(connection):
    """
    Sales by product: each product with the units sold and the revenue, highest revenue first.
    """
    rows = connection.execute(
        """
        SELECT p.name AS product_name,
        p.id AS product_id,
        COALESCE(SUM(s.quantity), 0) AS units_sold,
        COALESCE(SUM(s.quantity * s.unit_price), 0) AS revenue
        FROM products AS p
        LEFT JOIN sale_items AS s ON p.id = s.product_id
        GROUP BY p.id
        ORDER BY revenue DESC, p.id
        """
    ).fetchall()

    return rows


def never_sold(connection):
    """
    Never sold: products that appear in no sale.
    """
    rows = connection.execute(
        """
        SELECT p.name AS product_name,
        p.id AS product_id
        FROM products AS p
        LEFT JOIN sale_items AS s ON p.id = s.product_id
        WHERE s.sale_id IS NULL
        """
    ).fetchall()

    return rows
