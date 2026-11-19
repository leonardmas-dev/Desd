"""Exercise publication, Inventory handoff and the stock lifecycle on a local engine."""

import argparse
from contextlib import closing
from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3
import sys
import time
from urllib.request import urlopen
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "camunda/service-workers"))
from validation_worker import CamundaClient, producer_message

OUT = ROOT / "camunda/runtime/sprint2"


def find(client, collection, **filters):
    return client.post(f"/{collection}/search", {"filter": filters, "page": {"limit": 100}})["items"]


def wait_for(check, description):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.35)
    raise RuntimeError(f"Timed out waiting for {description}. Inspect Operate and the worker logs.")


def scope(client, instance):
    return {row["name"]: json.loads(row["value"])
            for row in find(client, "variables", scopeKey=instance) if not row.get("isTruncated")}


def instance_key(client, run_value, process):
    def locate():
        for row in find(client, "variables", name="productId", value=json.dumps(run_value)):
            key = row["processInstanceKey"]
            if row["scopeKey"] != key:
                continue
            with urlopen(f"{client.base}/process-instances/{key}", timeout=5) as response:
                instance = json.load(response)
            if instance["processDefinitionId"] == process:
                return key
        return None
    return wait_for(locate, f"{process} instance for {run_value}")


def complete_at(client, key, element, state="COMPLETED"):
    return wait_for(lambda: find(client, "element-instances", processInstanceKey=key,
                                 elementId=element, state=state), f"{element} ({state})")


def run(client, catalogue, product_name):
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    today = date.today()
    sample = json.loads((ROOT / "camunda/examples/submission.json").read_text())
    product = product_name + "-" + uuid.uuid4().hex[:8]
    sample.update(productId=product, availableStart=(today-timedelta(days=2)).isoformat(),
                  availableEnd=(today+timedelta(days=7)).isoformat())

    def stored():
        with closing(sqlite3.connect(catalogue)) as db:
            row = db.execute("SELECT payload FROM products WHERE product_id=?", (product,)).fetchone()
        return json.loads(row[0]) if row else None

    def record(step, key, **expect):
        current = stored()
        assert current, (step, "catalogue record missing")
        assert all(current[name] == value for name, value in expect.items()), (step, current)
        assert not client.post(f"/process-instances/{key}/incidents/search", {})["items"]
        row = {"step": step, "processInstanceKey": key, "productId": product, **expect}
        results.append(row)
        print(json.dumps(row), flush=True)

    def send_inventory(message, **values):
        event_id = uuid.uuid4().hex
        client.publish(message, product, {"productId": product, "demoEventId": event_id, **values}, event_id)
        def locate():
            for row in find(client, "variables", name="demoEventId", value=json.dumps(event_id)):
                if row["scopeKey"] == row["processInstanceKey"]:
                    return row["processInstanceKey"]
            return None
        return wait_for(locate, message)

    filename = OUT / "submission.json"
    filename.write_text(json.dumps(sample, indent=2) + "\n")
    producer_message(client, filename)
    validation_key = instance_key(client, product, "Process_ProductValidation")
    complete_at(client, validation_key, "End_ProductPublished")
    assert scope(client, validation_key)["certificationResult"] == "valid"
    key = instance_key(client, product, "Process_InventoryManagement")
    complete_at(client, key, "End_InventoryRecordInitialised")
    record("Verified publication", validation_key, published=True, organicBadge=True)
    record("Inventory started by publication", key, inventoryInitialised=True,
           stockQuantity=10, available=True)

    key = send_inventory("CustomerOrder", orderQuantity=3)
    complete_at(client, key, "End_ProductStillAvailable")
    record("Order leaves remaining stock", key, stockQuantity=7, available=True)

    key = send_inventory("CustomerOrder", orderQuantity=7)
    complete_at(client, key, "End_ProductOutOfStock")
    record("Zero stock is unavailable", key, stockQuantity=0, available=False)

    key = send_inventory("RestockStarted", restockAmount=5, seasonalStartDate=sample["availableStart"],
                         seasonalEndDate=sample["availableEnd"])
    complete_at(client, key, "End_ProductAvailable")
    record("In-season restock restores availability", key, stockQuantity=5, available=True)

    key = send_inventory("RestockStarted", restockAmount=2,
                         seasonalStartDate=(today-timedelta(days=12)).isoformat(),
                         seasonalEndDate=(today-timedelta(days=2)).isoformat())
    complete_at(client, key, "End_SeasonalProductArchived")
    record("Out-of-season restock stays unavailable", key, stockQuantity=7, available=False)

    key = send_inventory("RestockStarted", restockAmount=-1,
                         seasonalStartDate=sample["availableStart"], seasonalEndDate=sample["availableEnd"])
    complete_at(client, key, "End_RestockCorrectionRequested")
    record("Invalid restock asks for correction", key, stockQuantity=7, available=False)

    key = send_inventory("CustomerOrder", orderQuantity=8)
    complete_at(client, key, "Task_InvestigateInventoryError", "ACTIVE")
    task = wait_for(lambda: find(client, "user-tasks", processInstanceKey=key,
                                 elementId="Task_InvestigateInventoryError"),
                    "Inventory investigation task")
    client.post(f"/user-tasks/{task[0]['userTaskKey']}/completion",
                {"variables": {"resolution": "escalated", "adminNotes": "Test order rejected safely."}})
    complete_at(client, key, "End_InventoryErrorHandled")
    record("Unavailable or excessive order reaches investigation", key, stockQuantity=7, available=False)

    rejected_product = product + "-invalid-cert"
    rejected = {**sample, "productId": rejected_product, "organicCertNum": "UNKNOWN-CERTIFICATE"}
    rejected_file = OUT / "invalid-certificate.json"
    rejected_file.write_text(json.dumps(rejected, indent=2) + "\n")
    producer_message(client, rejected_file)
    key = instance_key(client, rejected_product, "Process_ProductValidation")
    complete_at(client, key, "Catch_CorrectedDetails", "ACTIVE")
    assert scope(client, key)["certificationResult"] == "invalid"
    assert not client.post(f"/process-instances/{key}/incidents/search", {})["items"]
    keys = {item["processInstanceKey"] for item in
            find(client, "variables", name="productId", value=json.dumps(rejected_product))}
    for related in keys:
        with urlopen(f"{client.base}/process-instances/{related}", timeout=5) as response:
            assert json.load(response)["processDefinitionId"] != "Process_InventoryManagement"
    with closing(sqlite3.connect(catalogue)) as db:
        assert db.execute("SELECT 1 FROM products WHERE product_id = ?", (rejected_product,)).fetchone() is None
    rejection = {"step": "Invalid certificate creates no Inventory handoff", "processInstanceKey": key,
                 "productId": rejected_product, "published": False, "inventoryStarted": False}
    results.append(rejection)
    print(json.dumps(rejection), flush=True)

    (OUT / "rehearsal-results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    entries = run(CamundaClient("http://127.0.0.1:18080"), args.db, "BRFN-DEMO")
    print(f"{len(entries)} connected checks passed.")
