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
