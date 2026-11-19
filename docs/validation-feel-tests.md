# Validation FEEL Evaluation Record

Current status (18 November 2026): the reconciled call-activity parent, certification child and three form IDs were deployed to the development cluster on 17 November. A new version-5 engine instance reached manual review after exactly three timed-out calls, and Operate shows all three called instances cancelled. Tasklist loaded the linked review form and allowed Ahmed to claim it. Validation output was supplied through Test mode; an authenticated Python-worker run is still outstanding. Today's local compatibility change accepts the newer team form date names without changing the Inventory model or original forms. See the final section for details. Earlier undeployed, missing-form and worker-prerequisite statements are historical.

These are actual evaluations with feelin 8.2.0, the evaluator used by the standalone playground linked in the Week 10 FEEL lab. Expressions were read from the current BPMN source. The leading Camunda expression marker was removed for evaluation as instructed by the lab.

The input contract requires `validationPassed` and `organicClaimed` to be Booleans. The validation worker must reject missing, null or wrongly typed organic-claim input before it reports validation success. A worker must return a correctly typed Boolean `validationPassed`. Thierno’s Card 33 owns this worker implementation. Cards 29 and 36 configure executable routing around that contract.

| Flow or message | Raw FEEL | Input type | Input JSON | Expected | Actual | Diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| F_Valid | `validationPassed = true` | Boolean true | `{"validationPassed":true}` | `true` | `true` | None |
| F_Valid | `validationPassed = true` | Boolean false | `{"validationPassed":false}` | `false` | `false` | None |
| F_Valid | `validationPassed = true` | Null | `{"validationPassed":null}` | `false` | `false` | None |
| F_Valid | `validationPassed = true` | String | `{"validationPassed":"true"}` | `null` | `null` | None |
| F_Valid | `validationPassed = true` | Number | `{"validationPassed":1}` | `null` | `null` | None |
| F_Valid | `validationPassed = true` | Context | `{"validationPassed":{}}` | `null` | `null` | None |
| F_Valid | `validationPassed = true` | Missing | `{}` | `false` | `false` | Variable 'validationPassed' not found |
| F_Organic | `organicClaimed = true` | Boolean true | `{"organicClaimed":true}` | `true` | `true` | None |
| F_Organic | `organicClaimed = true` | Boolean false | `{"organicClaimed":false}` | `false` | `false` | None |
| F_Organic | `organicClaimed = true` | Null | `{"organicClaimed":null}` | `false` | `false` | None |
| F_Organic | `organicClaimed = true` | String | `{"organicClaimed":"true"}` | `null` | `null` | None |
| F_Organic | `organicClaimed = true` | Number | `{"organicClaimed":1}` | `null` | `null` | None |
| F_Organic | `organicClaimed = true` | Context | `{"organicClaimed":{}}` | `null` | `null` | None |
| F_Organic | `organicClaimed = true` | Missing | `{}` | `false` | `false` | Variable 'organicClaimed' not found |
| Msg_Corrected | `submissionId` | String | `{"submissionId":"BRFN-UC1-001"}` | `"BRFN-UC1-001"` | `"BRFN-UC1-001"` | None |
| Msg_Corrected | `submissionId` | Missing | `{}` | `null` | `null` | Variable 'submissionId' not found |

## Interpreting the results

For correctly typed Boolean inputs, true selects the labelled Yes flow and false uses the explicit default No flow. Null equality and missing-variable behaviour are recorded as observed. Wrongly typed values can produce null instead of false. These invalid inputs require correction at the data source. Their evaluator results do not establish safe runtime routing or recovery from expression errors.

The correction catch requires a unique string `submissionId` created at initial submission and reused as the correction message correlation key. Missing identity produces null with a diagnostic and must be supplied before a waiting-message subscription opens. This follows the correlation-key technique in Week 10, adapted from orderId to a product submission identifier.

Both Boolean gateway default flows have no conditions. The default path does not repair malformed expressions or data.

## Model walkthroughs

| Scenario | Expected path | Evidence type |
| --- | --- | --- |
| Valid non-organic details | Validate, Yes, Organic claimed No, Publish | BPMN graph walkthrough plus evaluated Boolean conditions |
| Valid organic details and successful verifier | Validate, Yes, Organic claimed Yes, Check certification, Publish after verifier success | BPMN graph walkthrough plus evaluated Boolean conditions |
| Invalid details then corrected non-organic data | Validate, No, Request corrections, receive corrected message, validate again, Yes, No organic claim, Publish | BPMN graph walkthrough plus evaluated Boolean conditions |
| Repeated invalid submissions | Repeat correction loop until validation succeeds | BPMN graph walkthrough |
| Certification invalid | Route to producer correction and revalidate corrected details | FEEL evaluation and offline graph execution |
| Verifier unavailable or times out | Count failures after the retry delay; retry while fewer than three failures; then manual review | FEEL evaluation, offline graph execution and engine timeout test |

These walkthroughs distinguish FEEL evaluation, model structure validation and graph checks as the lab requires. They alone do not demonstrate worker execution or deployment; the later section records the separate development-engine evidence.

## Teaching references

- `Week 10 - FEEL Expressions Technical Lab.docx`, Exercises 2, 4 and 5.
- `Week 8 Tutorial.docx`, Implement Mode and job-worker explanation.
- `Task 1 - Use Cases.pdf`, page 1.

## Cards 29 and 36 executable configuration (14 November 2026)

Marketplace process ID remains `Process_ProductValidation`; only Marketplace is executable. Producer activities remain descriptive. All catching message definitions now use `submissionId` correlation, including the descriptive producer pool because the deployment validator checks those definitions too.

| Variable | Type / producer | Use |
| --- | --- | --- |
| submissionId | Unique string from initial submission | Reuse for corrected-message correlation |
| validationPassed | Boolean from validate-product-details | True allows the organic-claim gateway |
| validationErrors | List from validate-product-details | Clear correction feedback |
| organicClaimed | Boolean checked by validation worker | True requires certification |
| certificationResult | String from verify-organic-cert | valid publishes; invalid corrects; unavailable retries; unrecognized strings/null take the default review path; wrong types can raise an expression incident |
| certificationFailures | Number managed by BPMN output mappings | Reset after validation / human review; increment on retry timer completion |
| certificationTimeout | ISO 8601 duration string, optional | Interrupt each verification attempt; PT30S demonstration fallback |
| certificationRetrySeconds | Positive number, optional | Base delay in seconds, doubled per failure (base, 2×base, 4×base); demonstration fallback 1 second |
| reviewApproved | Boolean from Leonard’s Card 32 manual review form | True retries verification; false requests correction |

The three-attempt limit follows the existing team functionality document. Timeout/base-delay values are configurable demonstration settings, not additional Use Case 1 requirements. Human approval does not bypass verification. Technical job failures retain Zeebe retry/incident behavior; explicit business unavailability is either `certificationResult = "unavailable"` or BPMN error `SERVICE_UNAVAILABLE`. A generic failed job does not trigger an error boundary event.

The worker job types remain `validate-product-details`, `verify-organic-cert`, `publish-product`, `notify-product-published`, and `request-product-correction`. Card 33 supplies actual service behavior. The review task uses candidate group `marketplace-reviewers`; Card 32 supplies and links its form.

### Additional offline checks

34 actual FEEL evaluations cover certificate outcomes (including unknown/null/wrong-type values), retry limits, review decisions, counter increments, exponential backoff and both timer settings. Ten graph executions cover non-organic publication, valid certification, invalid certification, unavailable/error/timeout followed by success, exhausted unavailable/timeout attempts, unexpected results, and retry after human review. These checks passed. The producer activity/sequence-flow signatures are unchanged from the Git baseline.

BPMN moddle import: zero warnings. Camunda 8.9 and 8.10 compatibility lint: zero errors and one missing-form warning for the review task. This warning remains until Card 32 is integrated.

### Development deployment and engine evidence

Shared resource: https://hub.camunda.io/diagrams/f51ad097-61f6-4f4a-9d12-80ddbb64463f--validation/

Deployed to UWE Frenchay 2026 / dev (Camunda 8.9+gen27). Operate verified `Process_ProductValidation`, version 1.

Timeout test instance: `2251799867377404`. Mock validation output was supplied through Test mode; certification jobs were deliberately left unanswered. With PT2S timeout and PT0.1S retry delay, the engine interrupted exactly three verification jobs, persisted `certificationFailures = 3`, and activated `Task_ReviewCertification`. Publication was not reached.

Operate: https://lhr-1.api.camunda.io/848240b1-573c-4a07-bd52-723bea5b23b7/operate/processes/2251799867377404

This is engine execution with mocked worker output, not proof that Thierno’s simulated service or Leonard’s form is integrated. Taha’s Card 23 source is now available on `feature/taha-certification-sr-updates` and still needs reconciliation; it has not been merged into this model. The new resource preserves existing team diagrams. Full Card 36 simulated-service acceptance remains pending those integrations.

Service-result engine test: instance `6755399494721367` received mocked validation success, then a thrown `SERVICE_UNAVAILABLE` error, then an `unavailable` completion, then an `invalid` completion. The error boundary and result route each retried; failure count reached 2. Invalid certification activated `Task_RequestCorrection` and did not reach publication.

Valid-result engine test: instance `2251799867378361` received mocked validation success and `certificationResult = "valid"`; after mocked publish and confirmation completions, the instance reached Product published and COMPLETED. Service completion is mocked in Test mode and does not publish to an external marketplace.

Final exponential-backoff regression: `Process_ProductValidation` version 2, instance `4503599681039575`, was verified in Operate. With `certificationTimeout = "PT2S"` and `certificationRetrySeconds = 0.1`, the final timer expression ran successfully, exactly three verification attempts timed out, `certificationFailures` reached 3, and manual review was the active task. The base delay is doubled using FEEL; offline evaluations verify 0.1, 0.2 and 0.4 second values.

## Certification call-activity reconciliation (17 November 2026)

### Requirements and modelling decision

Use Case 1, page 1, requires mandatory product-information validation, correction of missing or invalid information, external or simulated verification when organic certification is claimed, and publication after required validation succeeds. It also asks the flow to consider verification-service unavailability and validation failure. It does not prescribe a retry count, a terminal rejection policy or automatic removal of an organic claim. The existing team functionality specification supplies the three-attempt limit, exponential retry and manual-review policy. The BPMN retains that policy without treating it as a new case-study requirement.

Week 8 Tutorial, Part 5, distinguishes the process engine from a service-task job worker: the worker performs the external interaction and completes the job. Week 8, Part 3, covers partial failure, timeouts, bounded retries and safe repetition. BPMN Classroom Lecture Slides, pages 7, 11, 24 and 25, distinguish subprocess detail, black-box participants, message flows and interrupting timer/error boundaries. The assessment brief, page 4, includes call activities, external interaction and executable processes in the operational modelling requirements.

Taha's call-activity and external-interaction design is retained. The called process is now an executable marketplace verification adapter with a none start event and a service task using job type `verify-organic-cert`. The independent external service is a black-box pool in the called-process diagram; its internal implementation is not asserted. The two message flows describe the worker's request and response, rather than starting another Camunda process. The worker must perform that interaction; diagram arrows alone do not transmit messages.

Ahmed's result gateway, correction loop, interrupting error/timer boundaries, retry counter, exponential delay and human-review routing are retained. An invalid certificate requests correction and revalidation. It does not publish the organic claim, silently remove the claim or terminate the submission automatically. An unavailable service or timeout follows the bounded retry path. Manual approval starts another verification attempt and does not authorize publication by itself.

### Concrete source changes

- `models/validation.bpmn`: `Task_VerifyCertification` is a call activity with `zeebe:calledElement processId="Process_ExternalCertification"`, `latest` binding and an explicit `certificationResult` output mapping. Each attempt first resets its local result to null, preventing a previous valid result from being reused when a later worker returns no result. Both interrupting boundaries remain on this call activity. Decision-route geometry and message labels were clarified; producer activities and sequence-flow semantics remain unchanged.
- `models/certification-verification.bpmn`: Taha's `Process_ExternalCertification`, start/check/end IDs and external-service participant are carried into a separate editable resource. The process is executable and has a none start event. `Task_ExternalCertificationCheck` has job type `verify-organic-cert`. Completion returns the result through the call activity, so the former separate send-result task is not needed. The external service has no processRef and remains a black box.
- Both processes use the same string result contract: `valid`, `invalid`, `unavailable`. The explicit unavailability error code is `SERVICE_UNAVAILABLE`. A technical failed job continues to use Zeebe retries/incidents; it is not automatically treated as a thrown BPMN error.
- SVG and PNG exports exist for both resources under `bpmn/`. The combined SR remains consistent with checking claimed certification and publishing only after required checks.

### Current verification

BPMN moddle 10.3.1 with zeebe-bpmn-moddle 2.0.0 imported both resources with zero warnings. bpmn-js 18.31.1 rendered both with zero import warnings. Camunda compatibility lint 2.63.0 for both 8.9 and 8.10 reports zero errors and one warning: the parent manual-review user task still has no linked form. The called-process ID, executable flag, none start, worker type, boundary attachment, error code and selected output mapping were checked across both resources. The producer flow and all existing parent sequence-flow endpoints and conditions were compared with the pre-reconciliation model and are unchanged.

Seventeen offline graph executions passed, using 322 actual feelin 8.2.0 evaluations of expressions read from the BPMN, including repeated expression execution along the scenarios. This is an evaluation count, not 322 distinct test cases.

| Scenario | Checked result |
| --- | --- |
| Valid non-organic submission | Publishes without calling certification |
| Valid organic certification | One verification attempt, then publication |
| Invalid mandatory information | Producer correction, no publication |
| Invalid certification | Producer correction, no publication |
| Unavailable result, then valid | Retries, then publishes |
| SERVICE_UNAVAILABLE error, then valid | Error boundary route, retry, then publishes |
| Timeout, then valid | Timer boundary route, retry, then publishes |
| Three unavailable results | Manual review with failure count 3 |
| Three timeouts | Manual review with failure count 3 |
| Three explicit business errors | Manual review with failure count 3 |
| Unexpected result string | Manual review, no publication |
| Null result | Manual review, no publication |
| Previous valid result followed by omitted worker result | Result cleared; manual review, no publication |
| Review approves after three failures | Counter reset; fourth verification attempt returns valid before publication |
| Review rejects after three failures | Correction, no publication |
| Invalid certificate followed by corrected non-organic data | Revalidation occurs before publication |
| Child returns changes to retry count, organic claim or review decision | Only certificationResult is mapped back; parent state is preserved |

These are offline graph, expression, XML and rendering checks. Error propagation and child cancellation are checked as intended routing and against Camunda documentation; they have not been re-executed on the development engine for this reconciled version. Official references: [Camunda 8.9 call activities](https://docs.camunda.io/docs/8.9/components/modeler/bpmn/call-activities/) and [error events](https://docs.camunda.io/docs/8.9/components/modeler/bpmn/error-events/).

### Deployment and remaining integration

1. Import and deploy `models/certification-verification.bpmn` to the same cluster and tenant as the validation process. Its process ID must remain `Process_ExternalCertification`.
2. Import and deploy `models/validation.bpmn`. The static call reference uses the latest deployed child version at activation. Deploying the parent alone does not install its child process.
3. Card 33 must implement `verify-organic-cert` with the result/error contract above, plus the parent validation, publication and notification workers. Repeated verification must be safe for the same submissionId.
4. Card 32 must link the certification review form returning Boolean `reviewApproved` and verify reviewer assignment. The inventory investigation form is a separate form for a different process.
5. Run new development-engine instances covering valid, invalid, unavailable, explicit error, timeout, exhausted attempts, review approval and review rejection. In Operate verify child completion/error propagation and cancellation after timeout; confirm that no claimed organic product reaches publication without a valid check.

The reconciled source is pushed to `sprint-2-validation-execution` for review. The engine evidence above belongs to the earlier service-task version; the reconciled call-activity version still needs deployment and integrated engine testing. Full Card 36 service-and-form acceptance remains pending these integrations.

## Form and worker integration (17 November 2026, local implementation)

### Captured shared-model differences

The shared Camunda resource had diverged from the merged caller: validation, verification and publication were immediate script tasks. The validation script expected `category`, `unitPrice`, `startDate`, `endDate`, `postcode` and `allergens`, while the shared forms supply `productCategory`, `productPrice`, `availableStart`, `availableEnd`, `productOrigin` and `productAllergen`. An actual form-shaped payload failed that script's validation. Its verification script also defaulted a missing simulated result to `valid` and incremented the failure counter in addition to the retry timer. That counted two unavailable attempts as four failures instead of allowing the agreed three attempts.

The integration keeps the merged call activity and the existing form field names. It does not copy the divergent scripts over the caller. No inventory model, SR model or teammate's shared Camunda resource was edited during this local integration.

### Files and ownership

- `camunda/forms/SubmitProductDetails.form` and `CorrectProductDetails.form` are copies of Leonard's captured shared forms, with a required product description, optional relevant harvest/best-before date inputs and the existing positive initial-quantity rule aligned locally. Existing keys and category values are preserved. `ManualCertificationReview.form` is the captured review form, including its Boolean checkbox. The new local copies need the form owner's review before replacing shared versions.
- `models/validation.bpmn` links those three IDs and maps `validationMessage` so the correction form can display the feedback. Producer remains non-executable and descriptive; the Marketplace review task is executable. A form reference does not make the Producer pool run in Tasklist.
- `camunda/service-workers/validation_worker.py` supplies the five existing job types and external-producer submit/correct message commands, using the job-worker approach taught in Week 8. It is a new proposed integration implementation in the area of Card 33, whose team owner remains Thierno. His shared scripts have not been overwritten. The worker validates canonical form keys, calls the simulated HTTP verifier, persists a demonstration catalogue and emits correlated workflow messages. It never defaults an unknown certificate to valid or increments the BPMN failure counter.
- `camunda/service-workers/mock_certification.py` supplies the case-permitted simulated verification service, including controlled invalid, unavailable, error and delayed outcomes. Its local registry can recover without changing process variables. This is not an official certifier API.
- `camunda/README.md` gives deployment, existing-client configuration, demonstration commands and engine acceptance scenarios. The local SQLite catalogue demonstrates persistence; it does not integrate the separate live inventory database or replace its owners' tasks. Runtime data is ignored by Git.

### Verification of this integration

`python3 -m unittest discover -s camunda/tests -v`: **32 tests passed**. These cover actual loopback HTTP verification, unknown/missing certificate safety, explicit error and slow-request outcomes, cancelled completion handling, registry outage/recovery, form keys and IDs, Boolean claim validation, required data and dates, correction feedback, message correlation, single counter ownership, publication guards and idempotent SQLite persistence. They use fake Camunda REST responses, not a live engine. A previous certificate error cannot hide a new mandatory-field error after correction.

The actual BPMN expressions were also re-evaluated with feelin 8.2.0: **17 graph scenarios passed, using 340 evaluations**. This is an evaluation count, not 340 distinct cases. The three-unavailable, three-timeout and three-error routes each reach review with count 3. Approval causes a fresh verification attempt; rejection requests correction. Moddle imports have zero warnings; Camunda 8.9 and 8.10 compatibility lint has **zero errors and zero warnings**. The former local missing-review-form warning is resolved. Producer flow signatures and existing parent sequence-flow conditions are preserved. Visible diagram geometry is unchanged, so the existing BPMN exports remain representative.

### Still required for Card 36 acceptance

1. Compare the shared resources again for concurrent team edits, then import the three forms and deploy the called process and parent to the same development cluster and tenant.
2. Run these workers using an existing authorised cluster API client. Confirm `marketplace-reviewers` assignment and complete both review decisions in Tasklist.
3. Capture fresh Operate evidence for valid, invalid, unavailable, explicit error, timeout, three exhausted attempts and service recovery after review. Check that the timeout cancels the called child and that no organic product is published without a valid check. Earlier version-2 screenshots cannot substitute for this evidence.

No new shared deployment, live worker run, Tasklist assignment check or full Card 36 acceptance is established by these local results. Inventory workers, inventory integration, DMN and final team submission checks remain separate.

## Reconciled deployment and team-update compatibility (17–18 November 2026)

### Review of Thierno's service snapshot

Thierno's `7952a4f` on `sprint-2-validation-service-tasks` was compared with the corrected caller. All sequence-flow endpoints and conditions match; the snapshot uses immediate scripts for validation, certification and publication instead of the retained worker/call-activity design. Its validator uses the older field aliases, missing simulation input defaults to `valid`, and its verifier increments the counter in addition to the retry timer. The corrected model retains one counter owner and never treats absent verification input as success.

No source on Thierno's branch or on `main` was changed. An unfinished local merge of that older snapshot was cancelled when newer team commits arrived, so that the current team work can be reviewed before any further integration. `models/validation.bpmn` remains the Validation source of truth; the older duplicate at `bpmn/validation.bpmn` and space-suffixed PNG were not introduced into this branch.

### Deployment and engine evidence

Deployed to **UWE Frenchay 2026 / dev, Camunda 8.9+gen27**, on 17 November:

- Parent shared resource: [validation](https://hub.camunda.io/diagrams/f51ad097-61f6-4f4a-9d12-80ddbb64463f--validation/).
- Child shared resource: [certification-verification](https://hub.camunda.io/diagrams/0dad87d6-8c44-4cb5-a958-266ade58753d--certification-verification/), process ID `Process_ExternalCertification`, engine version 1.
- Form IDs: `SubmitProductDetails`, `CorrectProductDetails`, `ManualCertificationReview`. The first two were imported as **SubmitProductDetails (Integrated)** and **CorrectProductDetails (Integrated)**, preserving Leonard's original resources. The review form was reused unchanged. Form deployments reported success.
- Parent process ID `Process_ProductValidation`, engine **version 5**, instance **2251799867646117**, submission ID `AHMED-C29-CALL-20261117-01`.

The test published the submission message with canonical form-shaped data, `certificationTimeout = "PT2S"` and retry base 0.1 seconds. The validation result was manually supplied in Test mode, including `validationMessage`. Certification jobs were deliberately left unanswered. The real engine invoked and interrupted the child three times, then activated `Task_ReviewCertification` with `certificationFailures = 3`. It did not reach publication.

Called child instances **2251799867646258**, **2251799867646304** and **2251799867646351** are shown cancelled in Operate. This establishes cancellation of the called processes, rather than only an offline routing expectation.

Tasklist task **2251799867646398** rendered **ManualCertificationReview** with the product and certificate numbers. Candidate group `marketplace-reviewers` was visible, and Ahmed successfully claimed it. An unchecked review decision was submitted. A fresh Operate inspection on 18 November confirms `reviewApproved = false` followed the review decision gateway into the correction path and reached `Task_RequestCorrection`, without publication. The failure count was reset to 0 as defined by the review output mapping. The test instance is now closed; this route evidence does not establish completion of the whole workflow. This verifies rendering and assignment for this account, not every intended reviewer's access.

Evidence is retained under `docs/evidence/validation/2026-11-17/`, including [version-5 timeout/review](evidence/validation/2026-11-17/operate-timeout-review-v5.png), [three cancelled children](evidence/validation/2026-11-17/operate-cancelled-children-v5.png), form deployment confirmations and the Tasklist review form. [Open the parent instance in Operate](https://lhr-1.api.camunda.io/848240b1-573c-4a07-bd52-723bea5b23b7/operate/processes/2251799867646117/variables).

The rejection-route screenshot is retained at [review rejection to correction](evidence/validation/2026-11-18/review-rejection-route.png).

These results do **not** establish a connected Python-worker run or full Card 36 acceptance. No API client was created and no credentials were added to the repository. The client-access decision remains pending.

### Preserving the newer team work

On 18 November, `main` advanced to **1ad55f8**. Yaseen's Inventory work was merged through PR 3, and Leonard added five original form exports under `Forms 2/`. The Inventory receiver now defines `brfn.inventory.product-listed`, `Start_ProductListed` and worker type `brfn.inventory.initialise`. Its input mappings expect `availableStart` / `availableEnd` and map them to seasonal dates.

Leonard's new submission/correction forms supply `seasonalStartDate` / `seasonalEndDate` and do not yet include a description field. The Validation worker now accepts either date pair and preserves both representations in its demonstration catalogue. If both are supplied with different values, validation requests correction. A missing mandatory description still requests correction; date compatibility does not waive Case 1 requirements. The original team forms and Inventory model are unchanged by this patch.

Compatibility regression: **37 local tests passed** on 18 November, including five checks for seasonal-date input, conflicting dates, required description and safe catalogue persistence. These tests use local HTTP fixtures and temporary databases, not the shared engine. The new worker compatibility code has not yet had an authenticated cluster run.

Remaining integration work: agree the description-field change with the form owner; finish Validation's outgoing Inventory notification; connect an authorised worker client; execute the remaining valid/invalid/unavailable/error/review paths with the simulated service; and test the sender/receiver together. The receiver's presence alone does not establish the complete handoff.


### Read-only shared-model audit (18 November)

The shared project was inspected after access resumed. Validation had newer edits, with its project listing showing 22:41: a BRFN Platform pool label, a `Test Start` none start event (`Event_15ulqwg`), and script implementations for validation and publication. A downloaded read-only snapshot was compared locally; it was not imported back or used to overwrite the shared resource.

The current validation script uses the new seasonal date keys, but does not check the mandatory description or validate the organic-claim Boolean. The publication script sets `published = true`; it does not demonstrate the persistent catalogue implementation supplied by the local worker. The retained certification call activity is still present. These differences need a coordinated source decision before another shared deployment, so that active team testing is preserved. The creator shown in the project listing does not establish who made the latest edit.

This branch now includes `main` at `1ad55f8`. `models/inventory.bpmn` and every file under `Forms 2/` were compared against that revision and are byte-for-byte unchanged. No Inventory model or original team form was edited, and no shared Camunda resource was overwritten during the 18 November audit.

### Trello status recorded on 18 November

Card 29 is Done: executable configuration, separate form/child deployment, parent activation and invocation of the child have engine evidence. Card 36 remains In review: cancellation, exhausted timeouts and the rejected review route have evidence, but the remaining connected simulated-service scenarios have not passed on the engine. Both cards have a progress comment and relevant screenshots. Completion of Card 29 does not assert completion of the remaining service integration or Inventory handoff.


## Card 36 connected engine verification (18 November 2026)

The isolated Camunda 8.9.28 engine initially rejected the raw Validation BPMN because some incoming and outgoing references and event definitions were out of schema order, and the error definition followed the diagram. These elements were reordered. A structural comparison confirmed that the element values, routes, conditions and diagram geometry are identical. The engine then deployed both BPMN resources and all three forms in deployment `2251799813685318`.

The Python worker ran against the local engine through the REST API and called the repository's simulated certification service over HTTP. Test submissions used the repository CLI and synthetic product data. The checks read engine history and variables and inspected the persisted catalogue. The two review decisions were submitted through the local user task API. Tasklist rendering and assignment in the shared environment were checked separately in the earlier run.

| Check | Observed result |
| --- | --- |
| Valid organic certificate | Child completed, product published with organic badge |
| Non-organic submission | Published without a certification call or badge |
| Invalid certificate | Reached correction with feedback and no publication |
| Corrected certificate | Same submission revalidated before publication |
| Missing product description | Requested correction without certification or publication |
| Explicit service error and rejected review | Error boundary caught all three errors, then rejection requested correction without publication |
| Slow verifier | Timer fired on all three attempts, cancelled all three children and opened manual review |
| HTTP 503 outage | Three unavailable results reached review with failure count 3, without publication |
| Approved retry after service recovery | A fourth child checked the certificate successfully before publication |

All nine checks passed across seven instances with no incidents. The 37 Python regression tests passed again. The detailed [engine results](evidence/validation/2026-11-18/card-36-engine-results.json), [Operate timeout and review](evidence/validation/2026-11-18/timeout-review-operate.jpg) and [three cancelled calls](evidence/validation/2026-11-18/timeout-children-operate.png) are retained here.

This completes Card 36's simulated service tests. The team still needs to reconcile the newer shared Validation model and run the separate Validation to Inventory handoff. The test used the repository's Validation worker and local Camunda, so a connected run on the shared class cluster remains unverified. The shared model, Inventory and the original team forms were preserved.
