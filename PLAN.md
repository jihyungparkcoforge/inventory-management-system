# Inventory Management System

A small hardware store keeps its stock in a spreadsheet. Prices drift, stock counts are wrong, and when a sale goes through, nobody can say exactly what changed. It keeps its data in a SQLite database with five related tables: suppliers, products, sales, the items in each sale, and a log of every stock movement.


## Tables

### suppliers

|X|id|name|
|---|---|---|
|**meaning**|supplier id|supplier name|
|**Note**| primary key| required |

Information such as contact and address can be added later, but these two is enough for this project.

### products

|X|id|sku|name|category|supplier_id|unit_price|quantity|reorder_level|
|---|---|---|---|---|---|---|---|---|
|**meaning**|product id|product code|product name|category of product|who selling this product|unit price in cent| quantity left|when product needed to reorder|
|**Note**|primary key|required, unique|required|required|required, foreign key (supplieres)|required (changable), integer, >=0|required, integer, >=0| required, integer, >=0 |

Both id and sku are unique id, but id is for internal db manage uses and sku for search from user end

### sales

|X|id|sold_at|
|---|---|---|
|**meaning**|sale id|date of sold|
|**Note**| primary key| required, date |

It store one specific invoice (transaction), so it have to connect with below sale_items to make it complete if we want to see what item is sold at specific transaction.
User information can be added, but it is out of scope for this assignment.

### sale_items

|X|sale_id|product_id|quantity|unit_price|
|---|---|---|---|---|
|**meaning**|sale id|product id|quantity of sold|unit price of buying moment in cent|
|**Note**| foreign_id (sales) | foreign_id (products) | required, integer, >0| required, integer, >=0|

Combination of sale_id and product_id is used for primary key.

### stock_movements

|X|id|product_id|quantity_change|reason|occurred_at|
|---|---|---|---|---|---|
|**meaning**|change id|product id|quantity of change|reason of change (i.e., sold, restock)|when change heppend|
|**Note**| primary key | foreign_id (products) | required, integer | required, choice [sale, restock, adjustment] | required, date |



## Core public functions

| Function | Inputs | Returns / behavior |
|---|---|---|
| `connect` | database path | Connection with foreign keys on and named rows |
| `schema_excutor` | connection, schema path | `None`; creates the tables |
| `insert_rows` | connection, fixed table name, columns, rows | `None`; inserts rows without committing |
| `seed_data` | connection | `None`; inserts and commits sample data |
| `make_seed_db` | none; reads `INVENTORY_DB` | `None`; creates and seeds the database, prints row counts |
| `add_product` | connection, SKU, name, category, supplier name, price, quantity, reorder level | New product ID, or `False` for an unknown supplier |
| `get_product` | connection, product ID | Row including supplier name; raises `ValueError` if missing |
| `update_product` | connection, product ID, field, new value | `True` if updated, `False` if missing |
| `delete_product` | connection, product ID | `True` if deleted, `False` if missing or already sold; foreign key errors prevent deleting movement history |
| `search_products` | connection; optional SKU, name, supplier name, category, max price, in-stock and low-stock filters | Matching rows sorted by name |
| `stock_value` | connection | Supplier rows with stock value, highest value first |
| `low_stock` | connection | Products at or below reorder level, including units short |
| `sales_by_product` | connection | Product rows with units sold and revenue, highest revenue first |
| `never_sold` | connection | Products with no sale items |
| `restock` | connection, product ID, positive amount, optional time | `True` on success, `False` for invalid amount or missing product |
| `adjust` | connection, product ID, signed amount, optional time | `True` on success, `False` for invalid input, missing product, or negative final stock |
| `record_sales` | connection, product/quantity pairs, optional time | `True` on success, `False` for invalid items, unknown products, or insufficient stock |
| `backup_database` | source database path, backup folder | Path to the backup file |
| `print_row` | one row | `None`; prints money with two decimals |
| `main` | none; reads `INVENTORY_DB` and menu input | `None`; runs the menu and closes its connection on exit |
| `transaction` | connection; reads menu input | `None`; handles restock, adjustment, or sale |
| `manage_product` | connection; reads menu input | `None`; handles product lookup, CRUD, and search |
| `get_report` | connection; reads menu input | `None`; prints the selected report |

Prices are stored as integer cents. Database constraint errors propagate to the menu.
Stock changes use the current time when no time is supplied.

## Transaction plan

Restock, adjustment, and sale recording each use one transaction.
All changes are committed together. If any step fails, all changes
from that operation are rolled back.

Each operation uses one connection and one `with connection:` block.
Helper functions called inside the transaction do not commit on their own.
Errors are handled outside the transaction block.

The operation time is passed as a parameter, with the current time
as the default. Tests can pass a fixed time.

### Restock

1. Check that the product exists and the restock amount is a positive integer.
2. Increase `products.quantity` by the restock amount.
3. Add a row to `stock_movements` with the product ID, positive quantity
   change, reason `restock`, and operation time.
4. Commit after both the stock update and movement record succeed.

If any step fails, roll back the stock update and movement record.
The product quantity must remain unchanged.

### Adjust stock

1. Check that the product exists and the adjustment amount is an integer.
   The amount can be positive or negative.
2. Apply the adjustment to `products.quantity`.
   An adjustment that would make the quantity negative is refused.
3. Add a row to `stock_movements` with the signed quantity change,
   reason `adjustment`, and operation time.
4. Commit after both changes succeed.

If any step fails, roll back all changes from the adjustment.
No movement record should remain for a refused adjustment.

### Record a sale

1. Check the product and quantity pairs. Quantities must be positive
   integers, and the same product cannot appear twice.
2. Create a row in `sales` and get its ID.
3. For each product:
   - Check that the product exists and has enough stock.
   - Read its current unit price.
   - Add a row to `sale_items` using the sale ID, product ID,
     quantity, and price at the time of the sale.
   - Reduce `products.quantity` by the sold quantity.
   - Add a row to `stock_movements` with a negative quantity change,
     reason `sale`, and operation time.
4. Commit only after every product has been processed successfully.

If any step fails, roll back the entire sale, including:
- The new `sales` row.
- All new `sale_items` rows.
- All stock changes made by this sale.
- All movement records made by this sale.

For example, if the first product succeeds but the second product
does not have enough stock, the first product's stock must also return
to its original quantity. No part of the failed sale should remain.
Previously committed sales and movements stay unchanged.


## Release plan

### Version 1.0.0

Build the main features through five pull requests:

1. `feature/database-and-seed`
2. `feature/products-and-search`
3. `feature/reports`
4. `feature/stock-and-sales`
5. `feature/menu-and-container`

Each pull request must pass CI before merging.
CI checks include pytest, ruff, and a Docker build with tests run inside
the image once container support is added.

After verifying the features and data persistence with a Docker volume,
create Git tag `v1.0.0` and Docker image tag `1.0.0`.
Add an entry to `CHANGELOG.md`.

### Version 1.1.0

Use `feature/low-stock-banner` for the sixth pull request.
Add a banner showing the number of low stock products when the menu starts.

After CI passes and the pull request is merged, create Git tag `v1.1.0`
and Docker image tag `1.1.0`. Update `CHANGELOG.md`.

### Backup and rollback

Before upgrading, back up the database using SQLite's backup function.
Verify the backup with `PRAGMA integrity_check` and matching table row counts.
Test restoring the backup with the application stopped.

Run version 1.1.0, then roll back to 1.0.0 using the same Docker volume.
Check that the banner is gone and the saved data remains intact.

Record the actual build, persistence, backup, restore, and rollback
results in `README.md`. Push both Git tags to GitHub and confirm
that the latest CI run on main passes.
