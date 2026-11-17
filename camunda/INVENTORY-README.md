# BRFN Inventory worker — development handoff

This is a **local prototype**, not a deployed or end-to-end tested Camunda solution. It uses Python standard library and the `products(product_id, submission_id, payload)` SQLite demonstration table from the Validation worker branch.

## Included job types
- `update-stock` — persist stock quantity and seasonal dates
- `unpublish-stock` — ensure out-of-stock product is unavailable
- `republish-product` — reactivate positive-stock, in-season product
- `deduct-inventory` — deduct quantity without overselling
- `check-restock-details` — produce `validationPassed`
- `brfn.inventory.initialise` — idempotent record initialisation (does not overwrite an existing published record)

## Local tests
From this folder: `python -m unittest -v test_inventory.py`

## Camunda worker start (only after cluster access is arranged)
Set `CAMUNDA_REST_URL` to your cluster's Camunda 8 REST API endpoint (e.g. `https://.../v2`), `CAMUNDA_BEARER_TOKEN` to an authorised token, and `BRFN_CATALOGUE_DB` to the **same** SQLite database path used by Validation. Then run `python inventory_worker.py --run`.

## Important integration blockers — resolve before claiming Card 26 or Card 34 done
1. No live Camunda cluster connection or end-to-end process tests were available here. The seven passing tests are **offline unit tests**.
2. The supplied Validation BPMN still lacks the agreed post-publication Inventory notification. A separate Validation-side message-publishing job/connector must be added after publication and the Inventory message start event must receive `brfn.inventory.product-listed` with `productId`, `stockQuantity`, `availableStart`, `availableEnd`.
3. Camunda 8 service task Job Types are present, but retry counts are empty on most tasks. Set and verify them in coordination with the team.
4. BPMN gateway defaults and variables must be reviewed, including the `Stock <= 0?` and seasonal conditions. `check-restock-details` must be given the expected variables.
5. The existing BPMN error boundary events and worker errors need to be aligned. This prototype reports business failures as job failures/incidents, **not BPMN errors**; it will not automatically trigger those boundary error paths.
6. For a real system, deduction needs an idempotency key (order ID) to avoid double-deduction if a worker commits to the DB but fails before Camunda acknowledges job completion. Likewise, stock updates need update IDs/versioning to prevent repeated or stale updates.
7. The demo database is SQLite. A shared deployment requires a shared durable datastore, transaction and concurrency design; local copies of SQLite are not shared between machines.
8. The worker currently accepts a supplied bearer token only; for hosted environments use a supported OAuth token-refresh mechanism or adapt the existing team's Camunda client.
9. The process has additional send/user tasks and message events; full end-to-end completion depends on their implementation and on the teammates' conditions/error/DMN work.
10. The local tests use a fixed 2026-11-17 date where relevant. The live worker uses the current system date.

## Suggested verification after deployment
Publish a new product through Validation, confirm Inventory initialisation; start an order, confirm deduction and zero-stock unpublishing; send restock update, confirm quantity/date persistence and conditional republishing; test invalid dates, out-of-season, overselling and worker failure paths. Capture Camunda Operate evidence and DB before/after snapshots.

Do not commit this directly to shared `main`. Review on a separate Inventory branch and coordinate with teammates first.
