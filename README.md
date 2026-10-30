# inventory-management-system

## Overview

A small hardware store keeps its stock in a spreadsheet. Prices drift, stock counts are wrong, and when a sale goes through, nobody can say exactly what changed. It keeps its data in a SQLite database with five related tables: suppliers, products, sales, the items in each sale, and a log of every stock movement.

## Quick Start

```{bash}
git clone https://github.com/jihyungparkcoforge/inventory-management-system.git
cd inventory-management-system
uv sync --locked
uv run python main.py
```

## Database Location

Set `INVENTORY_DB` to use a different database path.
If it is not set, the program uses `inventory.db` next to the code.
The Docker image defaults to `/data/inventory.db`.

## Running with Docker

```{bash}
docker build -t inventory-manage . --no-cache
docker run --rm -it \
  -v inventory-data:/data \
  inventory-manage
```

## Tests

```{bash}
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Backup and Restore

Choose 4. Backup Database from the main menu to create a backup.
The program uses SQLite's Connection.backup() and prints the saved file path.

Backups are stored in a backups folder next to the database:
- Local default: backups/
- Docker default: /data/backups/

Each backup includes a timestamp in its filename.
When /data is mounted to a volume, the backups remain available after the container is removed.

To restore a backup:

1. Exit the program and stop any container using the database.
2. Keep a separate copy of the current database.
3. Copy the selected backup to the active database path, replacing the database file.
4. Restart the program and check the restored data.


## Verification

The following checks were completed:

- Container persistence: Product 1's quantity was increased from 18 to 23. A new container using the same volume still showed 23.
- Backup integrity: PRAGMA integrity_check returned "ok" for the backup.
- Backup contents: All five tables had the same row counts and contents as the source database.
- Failed sale rollback: Tests confirmed that insufficient stock or an unknown product leaves stock unchanged and creates no sale, sale item, or stock movement records.
- Previous sales: Tests confirmed that a failed sale does not change previously committed sales or movements.


## 1.1.0 update

When the menu starts, it shows a banner with the number of low stock products.

## Release Rollback Verification

Versions 1.1.0 and 1.0.0 were tested using the same Docker volume.

1. Started version 1.1.0 and confirmed that the low-stock alert appeared.
2. Restocked Product 3 by 5 units, changing its quantity from 3 to 8.
3. Created a database backup and exited the container.
4. Started a new container with version 1.0.0 using the same volume.
5. Confirmed that the alert was gone and Product 3 still had 8 units.

The backup passed `PRAGMA integrity_check`, and all five tables matched
the source database. Restore was also tested on the verification database:
after changing Product 3's quantity to 99, restoring the backup returned it to 8.

This confirms that changing the application version preserves the database
when the same volume is used.

## Expected Report Results

These results use a fresh database with the provided seed data.
All prices and values are in cents. Results change after stock or sales operations.

### Stock Value by Supplier

Calculated as `SUM(quantity * unit_price)`, highest value first.

| Supplier | Stock value |
|---|---:|
| Bright Electrical | 51718 |
| Atlas Tools | 50154 |
| Cornerstone Hardware | 32347 |
| Clearflow Plumbing | 14941 |

### Low Stock

Products are included when `quantity <= reorder_level`.

| Product | Quantity | Reorder level | Units short |
|---|---:|---:|---:|
| Adjustable Wrench | 3 | 5 | 2 |
| PVC Elbow | 4 | 4 | 0 |

### Sales by Product

Revenue uses the price saved in `sale_items` at the time of sale,
not the current product price.

| Product | Units sold | Revenue |
|---|---:|---:|
| Claw Hammer | 2 | 3098 |
| LED Bulb | 6 | 2994 |
| Extension Cord | 1 | 1799 |
| Phillips Screwdriver | 2 | 1398 |
| Adjustable Wrench | 1 | 1299 |
| PVC Elbow | 3 | 747 |
| Hose Clamp | 2 | 698 |
| Wood Screws Pack | 1 | 599 |
| Electrical Tape | 2 | 598 |
| Thread Seal Tape | 2 | 398 |
| Wall Anchors Pack | 0 | 0 |
| Hex Nuts Pack | 0 | 0 |

### Never Sold

The following products have no matching rows in `sale_items`:

- Product 11: Wall Anchors Pack
- Product 12: Hex Nuts Pack

## Self-review

The most difficult part was understanding transactions. At first, I checked
whether stock changed, but that did not prove that a complete sale was saved.
A sale must update stock and create the sale, sale items, and stock movements
together. If any part fails, all changes from that sale must be rolled back.


The current test suite contains 23 passing tests. It covers several normal
and invalid cases, but the CLI and backup workflows still rely partly on
manual checks. Further improvements would include clearer input messages,
more backup tests, and simpler shared database setup code.
