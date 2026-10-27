PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier_id  INTEGER NOT NULL REFERENCES suppliers(id),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0)
) STRICT;

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    sold_at TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS sale_items (
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),

    PRIMARY KEY (sale_id, product_id),
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
) STRICT;

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER NOT NULL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity_change INTEGER NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('sale', 'restock', 'adjustment')),
    occurred_at TEXT NOT NULL
) STRICT;


CREATE INDEX IF NOT EXISTS idx_products_supplier_id
ON products(supplier_id);

CREATE INDEX IF NOT EXISTS idx_sale_items_product_id
ON sale_items(product_id);

CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id
ON stock_movements(product_id);
