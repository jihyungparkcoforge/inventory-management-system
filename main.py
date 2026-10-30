import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path

from product import (
    add_product,
    delete_product,
    get_product,
    search_products,
    update_product,
)
from report import low_stock, never_sold, sales_by_product, stock_value
from seed_db import connect, make_seed_db
from transaction import adjust, record_sales, restock

PROJECT_ROOT = Path(__file__).resolve().parents[0]


def main():
    db_path = Path(os.environ.get("INVENTORY_DB", str(PROJECT_ROOT / "inventory.db")))
    backup_folder = db_path.parent / "backups"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        make_seed_db()

    con = connect(str(db_path))

    print("""

-------------------------------------------------
|    Hello from inventory-management-system!    |
-------------------------------------------------

""")

    low_stock_rows = low_stock(con)

    print("*** Low Stock Alert!! ***")
    print(f"Low-stock products: {len(low_stock_rows)}")
    for row in low_stock_rows:
        print(dict(row))
    print("-------------------------\n")

    while True:
        i = input(
            "Menu:\n1. Transaction\n2. Manage Product\n3. Get Report\n4. Backup Database\n5. Exit\n"
        )
        if i not in ["1", "2", "3", "4", "5"]:
            print("Please choose from 1,2,3,4, or 5")
            continue

        menu = {"1": transaction, "2": manage_product, "3": get_report}
        if i == "4":
            try:
                print("backup made in :", backup_database(db_path, backup_folder))
            except (OSError, sqlite3.Error) as e:
                print(e)
            continue
        elif i == "5":
            con.close()
            sys.exit(0)

        menu[i](con)


def transaction(con):
    option = input("Options:\n1. Restock\n2. Adjust\n3. Sale\n4. Back\n")
    if option not in ["1", "2", "3", "4"]:
        print("Please choose from 1,2,3, or 4")

    if option == "1":
        data = input(
            "Please provide product id and amount you restocked (separate with comma)\n"
        )
        try:
            id, amount = [item.strip() for item in data.split(",")]
            id = int(id)
            amount = int(amount)
            success = restock(con, id, amount)
        except (ValueError, sqlite3.Error):
            print("Invalid input")
            return

        if success:
            print("Restock successfully saved!")
        else:
            print("Invalid input")
    if option == "2":
        data = input(
            "Please provide product id and amount you adjusted (separate with comma)\n"
        )
        try:
            id, amount = [item.strip() for item in data.split(",")]
            id = int(id)
            amount = int(amount)
            success = adjust(con, id, amount)
        except (ValueError, sqlite3.Error):
            print("Invalid input")
            return

        if success:
            print("Adjust successfully saved!")
        else:
            print("Invalid input")
    if option == "3":
        data = input(
            "Enter product ID and quantity, separated by commas.\n"
            "Example: 1 3,2 5,6 2\n> "
        )

        try:
            pair_list = []
            seen_ids = set()

            for item in data.split(","):
                product_id, quantity = item.split()
                product_id = int(product_id)
                quantity = int(quantity)

                if product_id <= 0 or quantity <= 0:
                    raise ValueError("Product ID and quantity must be positive.")

                if product_id in seen_ids:
                    raise ValueError("Each product can only appear once.")

                seen_ids.add(product_id)
                pair_list.append((product_id, quantity))

            success = record_sales(con, pair_list)

        except ValueError:
            print(
                "Invalid input. Enter positive ID/quantity pairs "
                "without duplicate products. Example: 1 3,2 5"
            )
            return

        except sqlite3.Error:
            print("Could not save the sale. Check the product IDs and data.")
            return

        if success:
            print("Sale successfully recorded!")
        else:
            print("Sale failed. Check product IDs and available stock.")
    if option == "4":
        return


def manage_product(con):
    option = input(
        "Options:\n1. Get\n2. Add\n3. Update\n4. Delete\n5. Search\n6. Exit\n"
    )
    if option not in ["1", "2", "3", "4", "5", "6"]:
        print("Please choose from 1,2,3,4,5, or 6")

    if option == "1":
        id = input("Please provide product id\n")
        try:
            row = get_product(con, int(id))
            if row:
                print(dict(row))
            else:
                print("Invalid input")
        except ValueError:
            print("Invalid input")
    if option == "2":
        data = input(
            "Please provide product sku, name, category, supplier (if new, new supplier will be added), unit price, quantity, and reorder level. (separate with comma)\n"
        )
        try:
            sku, name, category, supplier, price, quantity, reorder = [
                item.strip() for item in data.split(",")
            ]
            price = int(price)
            quantity = int(quantity)
            reorder = int(reorder)
            success = add_product(
                con, sku, name, category, supplier, price, quantity, reorder
            )
        except (ValueError, sqlite3.Error):
            print("Invalid input")
            return

        if success:
            print("Successfully added!")
        else:
            print("Invalid input")
    if option == "3":
        data = input(
            "Please provide product id, update field, and new value. (separate with comma)\nAllowed field: sku, name, category, supplier_id, reorder_level, unit_price\nUse Transaction > Adjust to change stock.\n"
        )
        try:
            id, field, value = [item.strip() for item in data.split(",")]
            id = int(id)
            success = update_product(con, id, field, value)
        except (ValueError, sqlite3.Error):
            print("Invalid input")
            return

        if success:
            print("Successfully updated!")
        else:
            print("Invalid input")

    if option == "4":
        try:
            id = int(input("Please provide product id\n"))
            success = delete_product(con, id)
        except (ValueError, sqlite3.Error):
            print("Invalid input or product has stock movement history.")
            return
        if success:
            print("Successfully deleted!")
        else:
            print("Invalid input or product has sales history.")

    if option == "5":
        data = input(
            "Select search filters, separated by commas.\n"
            "Press Enter to show all products.\n"
            "1. SKU\n"
            "2. Name\n"
            "3. Supplier name\n"
            "4. Category\n"
            "5. Max price (cents)\n"
            "6. In stock only\n"
            "7. Low stock only\n"
            "> "
        )

        field_list = [item.strip() for item in data.split(",")] if data.strip() else []

        text_fields = {
            "1": ("sku", "SKU"),
            "2": ("name", "Name"),
            "3": ("supplier_name", "Supplier name"),
            "4": ("category", "Category"),
        }

        filters = {}

        try:
            if any(
                field not in {"1", "2", "3", "4", "5", "6", "7"} for field in field_list
            ):
                raise ValueError("Select numbers from 1 to 7.")

            for field in dict.fromkeys(field_list):
                if field in text_fields:
                    key, label = text_fields[field]
                    value = input(f"{label}: ").strip()

                    if not value:
                        raise ValueError(f"{label} cannot be empty.")

                    filters[key] = value

                elif field == "5":
                    price = int(input("Max price in cents: ").strip())

                    if price < 0:
                        raise ValueError("Price cannot be negative.")

                    filters["max_price"] = price

                elif field == "6":
                    filters["in_stock_only"] = True

                elif field == "7":
                    filters["low_stock_only"] = True

        except ValueError:
            print("Invalid input")

        else:
            rows = search_products(con, **filters)

            if not rows:
                print("No products found.")
            else:
                for row in rows:
                    print(dict(row))
    else:
        return


def get_report(con):
    option = input(
        "Options:\n1. Stock values\n2. Low stocks\n3. Sales\n4. Never sold\n5. Exit\n"
    )
    if option not in ["1", "2", "3", "4", "5"]:
        print("Please choose from 1,2,3,4, or 5")
        return

    func = {"1": stock_value, "2": low_stock, "3": sales_by_product, "4": never_sold}

    if option == "5":
        return

    rows = func[option](con)
    for row in rows:
        print(dict(row))


def backup_database(source_path, backup_folder):
    source_path = Path(source_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"Database not found: {source_path}")

    backup_folder = Path(backup_folder)
    backup_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_folder / f"inventory-{timestamp}.db"

    with (
        closing(sqlite3.connect(source_path)) as source,
        closing(sqlite3.connect(backup_path)) as destination,
    ):
        source.backup(destination)

    return backup_path


if __name__ == "__main__":
    main()
