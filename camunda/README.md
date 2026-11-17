# Validation integration and demonstration

This folder supplies the three validation forms, the five job workers used by the
merged BPMN, a local simulated certification service and a local demonstration
catalogue. The workers use Python's standard library; no Python packages are required.
The job-worker design follows Week 8 Tutorial, Part 5. This implements the validation
and certification functionality; the separate inventory workers and DMN remain with
their existing task owners.

## Source of truth

- `models/validation.bpmn`: executable Marketplace process; descriptive external Producer pool.
- `models/certification-verification.bpmn`: executable certification adapter called by validation.
- `camunda/forms/*.form`: submission, correction and executable manual-review forms.
- `camunda/service-workers/validation_worker.py`: all five job types defined in the models.
- `camunda/service-workers/mock_certification.py`: simulated external HTTP verifier.

Do not replace the merged caller with the older Camunda script-task snapshot. The
captured shared forms have been retained, with description and relevant date inputs
added to submission/correction and their existing field names used by the worker.

## Deploy

1. Import the three `.form` files into the shared Camunda project. Keep IDs
   `SubmitProductDetails`, `CorrectProductDetails`, `ManualCertificationReview`.
2. Import and deploy `models/certification-verification.bpmn` first. Its process ID is
   `Process_ExternalCertification`.
3. Import and deploy `models/validation.bpmn` to the same cluster and tenant.
4. Check the manual-review task assignment to `marketplace-reviewers` with the team.
   The checkbox returns Boolean `reviewApproved`: checked retries verification;
   unchecked requests correction. It never grants publication directly.

Producer submission/correction tasks remain descriptive, as in the agreed model.
Attaching forms does not make a non-executable pool run in Tasklist. The commands
below act as the external producer interface using JSON with the same form keys.
The manual-review user task runs in Tasklist. An actual producer-facing web interface
is not supplied by these commands.

## Run the simulated service

From the repository root:

```sh
mkdir -p camunda/runtime
cp camunda/examples/certification-registry.json camunda/runtime/registry.json
python3 camunda/service-workers/mock_certification.py --allow-scenarios --state-file camunda/runtime/registry.json
```

The service listens only on `127.0.0.1:8090`. Without a scenario override it looks up
the supplied certificate number in the explicit local registry. Unknown or missing
certificates are invalid; missing simulation input never implies success.
`--allow-scenarios` enables controlled demonstration outcomes only. Leave it off for
a plain fixture-registry test. This is a mock service, not an official certifier API.

## Run the workers

In a second terminal, configure an **existing** API client authorised for the same
cluster and tenant. Use the REST URL and OAuth settings provided for that client:

```sh
export CAMUNDA_REST_URL='https://YOUR-CLUSTER-REST-ENDPOINT'
export CAMUNDA_TOKEN_URL='https://YOUR-EXISTING-OAUTH-TOKEN-ENDPOINT'
export CAMUNDA_CLIENT_ID='YOUR-EXISTING-CLIENT-ID'
export CAMUNDA_CLIENT_SECRET='YOUR-EXISTING-CLIENT-SECRET'
export CAMUNDA_TOKEN_AUDIENCE='zeebe.camunda.io'
# Set CAMUNDA_TENANT_ID too if the cluster uses a non-default tenant.
python3 camunda/service-workers/validation_worker.py worker
```

Alternatively supply an existing `CAMUNDA_BEARER_TOKEN`. It must remain valid while
the workers run; use OAuth settings above when automatic refresh is needed. Do not
commit credentials. The worker uses `/v2` automatically if it is absent from the URL.
No API client, permissions or credentials are created by this implementation.

The worker activates the exact job types `validate-product-details`,
`verify-organic-cert`, `publish-product`, `request-product-correction`, and
`notify-product-published`. Verification calls the local HTTP service. An explicit
service error becomes BPMN `SERVICE_UNAVAILABLE`; an unavailable result is completed
as `certificationResult = "unavailable"`. A slow request can be cancelled by the
parent timer; later completion of a cancelled job is handled without recreating it.

Publication writes to `camunda/runtime/catalogue.sqlite3` and is idempotent by product
ID. It checks validated data and successful certification before storing an organic
badge. This local catalogue is demonstration persistence, not the team's live
inventory database. Inventory integration remains a separate task.

## Submit and correct

With the same API settings, send the example's form-shaped data:

```sh
python3 camunda/service-workers/validation_worker.py submit --file camunda/examples/submission.json
```

Save the printed `submissionId`. For a correction, create a JSON file containing the
updated form fields **and that same submissionId**, then run:

```sh
python3 camunda/service-workers/validation_worker.py correct --file camunda/runtime/correction.json --submission-id YOUR-SAVED-SUBMISSION-ID
```

The commands publish `brfn.product.submitted` or `brfn.product.corrected` with matching
correlation. They whitelist product fields so a producer cannot inject
`validationPassed`, `certificationResult`, `certificationFailures` or `reviewApproved`.
Correction feedback includes `validationMessage`, which the correction form displays.
Review and notification commands are engine messages; no email or chat is sent.

## Card 36 engine scenarios

For quick controlled tests, add `certificationTimeout: "PT2S"` and
`certificationRetrySeconds: 0.1` to a copy of the example JSON. These are demonstration
settings, not case-study requirements. Use `simulatedCertification` only with the
mock service's `--allow-scenarios` flag:

| Input / situation | Expected result |
| --- | --- |
| No override and certificate `BRFN-VALID-001` | Registry verification succeeds, then publication |
| Unknown certificate / `invalid` | Producer correction, no publication |
| `unavailable` | One failure counted after each delay; third failed attempt reaches review |
| `error` | Parent error boundary catches SERVICE_UNAVAILABLE and uses the same retry path |
| `timeout` with PT2S parent timeout | Parent cancels the child before the delayed HTTP reply; third failure reaches review |
| Missing/wrongly typed mandatory data or organic flag | Clear correction feedback, no publication |
| Review checkbox unchecked | Requests correction |
| Review checkbox checked after service recovery | New verification occurs before publication |

To demonstrate recovery without changing process variables, omit a scenario override
and set `available` to false in the local registry JSON. After three failures, change
it back to true and approve retry in Tasklist. The next request re-reads the registry
and verifies the certificate again. Keep the original product and submission IDs.

Only the retry timer output mapping increments `certificationFailures`. Neither the
verification worker nor the called process increments it. The parent clears each
attempt's result and only maps `certificationResult` back from the child.

Capture new Operate and Tasklist evidence for these deployed resources. The earlier
version-2 engine screenshots do not prove this integration has run.

## Local checks

```sh
python3 -m unittest discover -s camunda/tests -v
```

These tests use loopback HTTP servers and temporary SQLite files, not a live Camunda
cluster. They cover real mock-verifier HTTP outcomes, message/API contracts, form
field alignment, publication guards, catalogue persistence, cancellation handling and
the single retry-counter owner. Live deployment, user assignment and timeout/error
propagation still require the engine scenarios above.

API references: [activate jobs](https://docs.camunda.io/docs/8.9/apis-tools/orchestration-cluster-api-rest/specifications/activate-jobs/),
[complete job](https://docs.camunda.io/docs/8.9/apis-tools/orchestration-cluster-api-rest/specifications/complete-job/),
[publish message](https://docs.camunda.io/docs/8.9/apis-tools/orchestration-cluster-api-rest/specifications/publish-message/).
