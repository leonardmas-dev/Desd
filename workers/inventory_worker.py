import asyncio
import logging
import os
from datetime import date, datetime
from pyzeebe import (
    ZeebeWorker,
    ZeebeClient,
    Job,
    create_camunda_cloud_channel,
    create_insecure_channel,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("inventory-worker")

# In-memory store to mock the inventory database for Sprint 3 testing
MOCK_INVENTORY_DB = {
    "PROD-001": {
        "productName": "Organic Somerset Apples",
        "stockQuantity": 10,
        "available": True,
        "seasonalStartDate": "2026-01-01",
        "seasonalEndDate": "2026-12-31",
    },
    "PROD-002": {
        "productName": "Heritage Carrots",
        "stockQuantity": 1,
        "available": True,
        "seasonalStartDate": "2026-01-01",
        "seasonalEndDate": "2026-12-31",
    },
}


def get_zeebe_channel():
    """Connects to Camunda Cloud if credentials are set, otherwise falls back to local Zeebe."""
    client_id = os.getenv("ZEEBE_CLIENT_ID")
    client_secret = os.getenv("ZEEBE_CLIENT_SECRET")
    cluster_id = os.getenv("ZEEBE_CLUSTER_ID")
    region = os.getenv("ZEEBE_REGION", "bru-2")

    if client_id and client_secret and cluster_id:
        logger.info("Connecting to Camunda Cloud cluster: %s", cluster_id)
        return create_camunda_cloud_channel(
            client_id=client_id,
            client_secret=client_secret,
            cluster_id=cluster_id,
            region=region,
        )

    address = os.getenv("ZEEBE_ADDRESS", "localhost:26500")
    logger.info("Connecting to local Zeebe broker at: %s", address)
    return create_insecure_channel(grpc_address=address)


async def on_task_error(exception: Exception, job: Job):
    """Logs unexpected Python exceptions and fails the Zeebe job so retries can run."""
    logger.error("Unhandled error in job %s (%s): %s", job.key, job.type, exception)
    await job.set_failure_status(f"Worker exception: {exception}")


def create_worker(channel) -> ZeebeWorker:
    worker = ZeebeWorker(channel)
    client = ZeebeClient(channel)

    # --- Product listing setup ---

    @worker.task(task_type="initialise-inventory", exception_handler=on_task_error)
    async def initialise_inventory(job: Job, **variables) -> dict:
        """Creates a starting stock record when a new product is listed."""
        product_id = variables.get("productId", "PROD-NEW")
        stock_qty = int(variables.get("stockQuantity", 0))
        start_date = str(variables.get("seasonalStartDate", "2026-01-01"))[:10]
        end_date = str(variables.get("seasonalEndDate", "2026-12-31"))[:10]

        MOCK_INVENTORY_DB[product_id] = {
            "productName": variables.get("productName", "New Listed Product"),
            "stockQuantity": stock_qty,
            "available": stock_qty > 0,
            "seasonalStartDate": start_date,
            "seasonalEndDate": end_date,
        }
        logger.info(
            "[initialise-inventory] Created record for %s (stock=%s, available=%s)",
            product_id,
            stock_qty,
            stock_qty > 0,
        )
        return {
            "inventoryStatus": "initialised",
            "available": stock_qty > 0,
        }

    # --- Order deduction and visibility ---

    @worker.task(task_type="deduct-inventory", exception_handler=on_task_error)
    async def deduct_inventory(job: Job, **variables) -> dict:
        """Subtracts ordered items from stock, or throws a BPMN error if stock is too low."""
        product_id = variables.get("productId", "PROD-001")
        order_qty = int(variables.get("orderQuantity", 1))
        simulate_error = variables.get("simulateDeductionError", False)

        logger.info(
            "[deduct-inventory] Processing order for productId=%s, orderQuantity=%s",
            product_id,
            order_qty,
        )

        # Allow forcing the error boundary path during testing
        if simulate_error or product_id == "ERR_DEDUCT":
            logger.warning(
                "[deduct-inventory] Throwing BPMN Error INVENTORY_DEDUCTION_FAILED for %s",
                product_id,
            )
            await job.set_error_status(
                error_code="INVENTORY_DEDUCTION_FAILED",
                message=f"Database error while deducting inventory for {product_id}",
            )
            return {}

        record = MOCK_INVENTORY_DB.setdefault(
            product_id,
            {
                "productName": variables.get("productName", "Unknown Product"),
                "stockQuantity": int(variables.get("stockQuantity", 1)),
                "available": True,
                "seasonalStartDate": variables.get("seasonalStartDate", "2026-01-01"),
                "seasonalEndDate": variables.get("seasonalEndDate", "2026-12-31"),
            },
        )

        current_stock = int(variables.get("stockQuantity", record["stockQuantity"]))

        if order_qty <= 0 or current_stock < order_qty:
            logger.warning(
                "[deduct-inventory] Not enough stock (current=%s, requested=%s). Throwing INVENTORY_DEDUCTION_FAILED.",
                current_stock,
                order_qty,
            )
            await job.set_error_status(
                error_code="INVENTORY_DEDUCTION_FAILED",
                message=f"Insufficient stock ({current_stock}) for order quantity ({order_qty})",
            )
            return {}

        new_stock = current_stock - order_qty
        record["stockQuantity"] = new_stock

        logger.info(
            "[deduct-inventory] Updated %s stock: %s -> %s",
            product_id,
            current_stock,
            new_stock,
        )
        return {
            "productId": product_id,
            "stockQuantity": new_stock,
        }

    @worker.task(task_type="unpublish-product", exception_handler=on_task_error)
    async def unpublish_product(job: Job, **variables) -> dict:
        """Hides the product from customers once stock hits zero."""
        product_id = variables.get("productId", "PROD-001")
        if product_id in MOCK_INVENTORY_DB:
            MOCK_INVENTORY_DB[product_id]["available"] = False
            MOCK_INVENTORY_DB[product_id]["stockQuantity"] = 0

        logger.info("[unpublish-product] Marked %s unavailable (available=False)", product_id)
        return {"available": False}

    # --- Restock checks and updates ---

    @worker.task(task_type="check-restock-details", exception_handler=on_task_error)
    async def check_restock_details(job: Job, **variables) -> dict:
        """Checks that restock quantity is positive and seasonal dates make sense."""
        product_id = variables.get("productId", "PROD-001")
        restock_qty = variables.get("restockQuantity")
        start_str = variables.get("seasonalStartDate")
        end_str = variables.get("seasonalEndDate")

        logger.info(
            "[check-restock-details] Validating productId=%s, restockQuantity=%s, dates=%s..%s",
            product_id,
            restock_qty,
            start_str,
            end_str,
        )

        validation_passed = False
        in_season = False
        reason = "OK"

        try:
            qty_val = int(restock_qty)
            if qty_val <= 0:
                reason = "restockQuantity must be greater than 0"
            elif not start_str or not end_str:
                reason = "seasonalStartDate and seasonalEndDate are required"
            else:
                start_dt = datetime.strptime(str(start_str)[:10], "%Y-%m-%d").date()
                end_dt = datetime.strptime(str(end_str)[:10], "%Y-%m-%d").date()
                if start_dt > end_dt:
                    reason = "seasonalStartDate cannot be after seasonalEndDate"
                else:
                    validation_passed = True
                    today_dt = date.today()
                    in_season = start_dt <= today_dt <= end_dt
        except (TypeError, ValueError) as exc:
            reason = f"Invalid input format: {exc}"

        if validation_passed and product_id in MOCK_INVENTORY_DB:
            MOCK_INVENTORY_DB[product_id]["seasonalStartDate"] = str(start_str)[:10]
            MOCK_INVENTORY_DB[product_id]["seasonalEndDate"] = str(end_str)[:10]

        logger.info(
            "[check-restock-details] Result for %s -> validationPassed=%s, inSeason=%s (%s)",
            product_id,
            validation_passed,
            in_season,
            reason,
        )
        return {
            "validationPassed": validation_passed,
            "inSeason": in_season,
            "validationMessage": reason,
        }

    @worker.task(task_type="update-stock-record", exception_handler=on_task_error)
    async def update_stock_record(job: Job, **variables) -> dict:
        """Adds the restocked units to the inventory record, or throws an update error."""
        product_id = variables.get("productId", "PROD-001")
        simulate_error = variables.get("simulateUpdateError", False)

        # Allow forcing the update error boundary path during testing
        if simulate_error or product_id == "ERR_UPDATE":
            logger.warning(
                "[update-stock-record] Throwing BPMN Error INVENTORY_UPDATE_FAILED for %s",
                product_id,
            )
            await job.set_error_status(
                error_code="INVENTORY_UPDATE_FAILED",
                message=f"Failed to persist stock update for {product_id}",
            )
            return {}

        record = MOCK_INVENTORY_DB.setdefault(
            product_id,
            {
                "productName": variables.get("productName", "Restocked Product"),
                "stockQuantity": 0,
                "available": False,
                "seasonalStartDate": str(variables.get("seasonalStartDate", "2026-01-01"))[:10],
                "seasonalEndDate": str(variables.get("seasonalEndDate", "2026-12-31"))[:10],
            },
        )

        current_stock = int(variables.get("stockQuantity", record["stockQuantity"]))
        restock_qty = int(variables.get("restockQuantity", 0))
        updated_stock = current_stock + restock_qty
        record["stockQuantity"] = updated_stock

        logger.info(
            "[update-stock-record] Updated %s stock: %s + %s = %s",
            product_id,
            current_stock,
            restock_qty,
            updated_stock,
        )
        return {"stockQuantity": updated_stock}

    @worker.task(task_type="republish-product", exception_handler=on_task_error)
    async def republish_product(job: Job, **variables) -> dict:
        """Makes the restocked product visible to customers again if it is in season."""
        product_id = variables.get("productId", "PROD-001")
        if product_id in MOCK_INVENTORY_DB:
            MOCK_INVENTORY_DB[product_id]["available"] = True

        logger.info("[republish-product] Restored availability for %s (available=True)", product_id)
        return {"available": True}

    # --- Producer notifications and message correlation ---

    @worker.task(task_type="notify-producer", exception_handler=on_task_error)
    async def notify_producer_zero_stock(job: Job, **variables) -> dict:
        """Logs a mock zero-stock alert and triggers the producer's restock start event."""
        product_id = variables.get("productId", "PROD-001")
        producer_email = variables.get("producerEmail", "producer@brfn-farm.co.uk")

        logger.info(
            "[MOCK NOTIFICATION -> PRODUCER] To: %s | Subject: Zero Stock Alert for %s (stockQuantity=0)",
            producer_email,
            product_id,
        )

        try:
            await client.publish_message(
                name="brfn.inventory.zero-stock-notice",
                correlation_key=str(product_id),
                variables={
                    "productId": product_id,
                    "stockQuantity": 0,
                    "available": False,
                },
            )
        except Exception as msg_err:
            logger.debug("Message publish info (brfn.inventory.zero-stock-notice): %s", msg_err)

        return {"zeroStockNotified": True}

    @worker.task(task_type="request-check-details", exception_handler=on_task_error)
    async def request_corrected_details(job: Job, **variables) -> dict:
        """Asks the producer to fix invalid restock details and correlates the catch event."""
        product_id = variables.get("productId", "PROD-001")
        producer_email = variables.get("producerEmail", "producer@brfn-farm.co.uk")
        reason = variables.get("validationMessage", "Invalid restock quantity or seasonal dates")

        logger.info(
            "[MOCK NOTIFICATION -> PRODUCER] To: %s | Subject: Action Required - Correct Restock Details for %s (%s)",
            producer_email,
            product_id,
            reason,
        )

        try:
            await client.publish_message(
                name="brfn.inventory.restock-correction-requested",
                correlation_key=str(product_id),
                variables={
                    "productId": product_id,
                    "validationMessage": reason,
                },
            )
        except Exception as msg_err:
            logger.debug("Message publish info (restock-correction-requested): %s", msg_err)

        return {"correctionRequested": True}

    @worker.task(task_type="confirm-stock-update", exception_handler=on_task_error)
    async def confirm_stock_update(job: Job, **variables) -> dict:
        """Confirms the product is live again and correlates the producer's catch event."""
        product_id = variables.get("productId", "PROD-001")
        new_stock = variables.get("stockQuantity", 0)
        producer_email = variables.get("producerEmail", "producer@brfn-farm.co.uk")

        logger.info(
            "[MOCK NOTIFICATION -> PRODUCER] To: %s | Subject: Stock Replenished & Live for %s (new stock=%s)",
            producer_email,
            product_id,
            new_stock,
        )

        try:
            await client.publish_message(
                name="brfn.inventory.stock-update-confirmed",
                correlation_key=str(product_id),
                variables={
                    "productId": product_id,
                    "stockQuantity": new_stock,
                    "available": True,
                },
            )
        except Exception as msg_err:
            logger.debug("Message publish info (stock-update-confirmed): %s", msg_err)

        return {"stockUpdateConfirmed": True}

    return worker


async def main():
    channel = get_zeebe_channel()
    worker = create_worker(channel)
    logger.info("Starting BRFN Inventory & Notification Zeebe workers (9 handlers registered)...")
    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())