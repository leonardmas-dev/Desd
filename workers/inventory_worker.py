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

# ---------------------------------------------------------------------------
# Mock In-Memory Inventory Store (replace with SQLite/Postgres if needed)
# ---------------------------------------------------------------------------
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
    """Supports both Camunda SaaS (Cloud) and local Self-Managed Zeebe."""
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
    logger.error("Unhandled error in job %s (%s): %s", job.key, job.type, exception)
    await job.set_failure_status(f"Worker exception: {exception}")


def create_worker(channel) -> ZeebeWorker:
    worker = ZeebeWorker(channel)
    client = ZeebeClient(channel)

    # =========================================================================
    # 1. PRODUCT LISTING INITIALISATION TASK
    # =========================================================================

    @worker.task(task_type="initialise-inventory", exception_handler=on_task_error)
    async def initialise_inventory(job: Job, **variables) -> dict:
        """
        Matches Service Task: Task_InitialiseInventoryRecord (type: 'initialise-inventory')
        Creates the initial inventory record when a newly validated product is listed.
        """
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

    # 