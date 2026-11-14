# Validation FEEL Evaluation Record

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
