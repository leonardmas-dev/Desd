"""Inventory jobs for the isolated Sprint 2 demo, sharing Validation's SQLite catalogue."""

import argparse
from contextlib import closing
from datetime import date
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlparse

from validation_worker import BusinessError, CamundaClient, Catalogue

JOB_TYPES = (
    "brfn.inventory.initialise", "deduct-inventory", "check-restock-details",
    "brfn.inventory.update-stock", "notify-producer", "request-check-details",
    "confirm-stock-update",
)
UPDATE_TYPES = {"brfn.inventory.initialise", "deduct-inventory", "brfn.inventory.update-stock"}
NOTICES = {
    "notify-producer": "ZeroStockNotice",
    "request-check-details": "brfn.inventory.restock-correction-requested",
    "confirm-stock-update": "brfn.inventory.stock-update-confirmed",
}


def restock_details(values):
    """Accept the form field and the process's quantity alias."""
    amount = values.get("restockAmount", values.get("restockQuantity"))
    if type(amount) is not int or amount <= 0:
        raise ValueError("Restock quantity must be a positive whole number.")
    start, end = (date.fromisoformat(values.get(key) or "") for key in
                  ("seasonalStartDate", "seasonalEndDate"))
    if start > end:
        raise ValueError("Seasonal end must be on or after the start.")
    return amount, start.isoformat(), end.isoformat()


def in_season(start, end):
    return start <= date.today().isoformat() <= end


class InventoryDemo:
    def __init__(self, path, client):
        self.path = Catalogue(path).filename
        self.client = client
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS inventory_demo_jobs "
                       "(job_key TEXT PRIMARY KEY, result TEXT NOT NULL)")

    def handle(self, job):
        kind = job["type"]
        data = job["variables"]
        if kind in UPDATE_TYPES:
            return self.update(kind, job["jobKey"], data)
        if kind == "check-restock-details":
            try:
                quantity, start, end = restock_details(data)
            except (ValueError, TypeError):
                return {"validationPassed": False, "validationMessage":
                        "Enter a positive whole quantity and valid seasonal dates in order."}
            return {"validationPassed": True, "restockQuantity": quantity,
                    "seasonalStartDate": start, "seasonalEndDate": end}
        payload = {key: data.get(key) for key in ("productId", "stockQuantity", "available",
                                                  "validationMessage")}
        if data.get("productId"):
            self.client.publish(NOTICES[kind], data["productId"], payload,
                                "inventory-notice-" + str(job["jobKey"]))
        return {"inventoryNoticeProcessed": True}

    def update(self, kind, job_key, data):
        product_id = data.get("productId")
        with closing(sqlite3.connect(self.path, timeout=15)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT result FROM inventory_demo_jobs WHERE job_key = ?",
                                  (job_key,)).fetchone()
            if previous:
                return json.loads(previous[0])
            row = db.execute("SELECT payload FROM products WHERE product_id = ?", (product_id,)).fetchone()
            if not row:
                code = ("INVENTORY_DEDUCTION_FAILED" if kind == "deduct-inventory"
                        else "INVENTORY_UPDATE_FAILED")
                raise BusinessError(code, "Product is missing from the publication catalogue.")
            product = json.loads(row[0])
            if kind == "brfn.inventory.initialise":
                if (product.get("published") is not True or
                        data.get("seasonalStartDate") is None or data.get("seasonalEndDate") is None):
                    raise ValueError("Inventory initialisation requires a published product and both mapped dates.")
                product["inventoryInitialised"] = True
            elif kind == "deduct-inventory":
                requested = data.get("orderQuantity")
                if (type(requested) is not int or requested <= 0 or
                        not product["available"] or not in_season(product["availableStart"], product["availableEnd"])
                        or requested > product["stockQuantity"]):
                    raise BusinessError("INVENTORY_DEDUCTION_FAILED", "Order exceeds available in-season stock.")
                product["stockQuantity"] -= requested
                if product["stockQuantity"] == 0:
                    product.update(available=False, catalogueStatus="UNAVAILABLE_OUT_OF_STOCK")
            else:
                try:
                    quantity, start, end = restock_details(data)
                except (ValueError, TypeError) as error:
                    raise BusinessError("INVENTORY_UPDATE_FAILED", "Invalid stock update.") from error
                available = in_season(start, end)
                product.update(stockQuantity=product["stockQuantity"] + quantity,
                               availableStart=start, availableEnd=end, seasonalStartDate=start,
                               seasonalEndDate=end, available=available,
                               catalogueStatus="ACTIVE" if available else "UNAVAILABLE_OFF_SEASON")
            result = {key: product[key] for key in ("productId", "stockQuantity",
                      "available", "catalogueStatus")}
            if kind == "brfn.inventory.initialise":
                result["inventoryInitialised"] = True
            db.execute("UPDATE products SET payload = ? WHERE product_id = ?",
                       (json.dumps(product), product_id))
            db.execute("INSERT INTO inventory_demo_jobs VALUES (?, ?)",
                       (job_key, json.dumps(result)))
            return result

    def run(self):
        while True:
            for kind in JOB_TYPES:
                for job in self.client.activate(kind, 4):
                    try:
                        result = self.handle(job)
                        self.client.complete(job, result)
                    except BusinessError as error:
                        self.client.throw(job, error)
                    except (ValueError, sqlite3.Error) as error:
                        self.client.fail(job, error)
            time.sleep(0.25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--engine", default="http://127.0.0.1:18080")
    args = parser.parse_args()
    if urlparse(args.engine).hostname not in ("localhost", "127.0.0.1", "::1"):
        parser.error("The Inventory demo worker requires a loopback Camunda engine.")
    InventoryDemo(args.db, CamundaClient(args.engine)).run()


if __name__ == "__main__":
    main()
