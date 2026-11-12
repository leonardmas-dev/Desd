# Validation FEEL Evaluation Record

These are actual evaluations with feelin 8.2.0, the evaluator used by the standalone playground linked in the Week 10 FEEL lab. Expressions were read from the current BPMN source. The leading Camunda expression marker was removed for evaluation as instructed by the lab.

The input contract requires `validationPassed` and `organicClaimed` to be Booleans. The validation worker must reject missing, null or wrongly typed organic-claim input before it reports validation success. A worker must return a correctly typed Boolean `validationPassed`. This worker implementation is still pending.

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

Both gateway default flows have no conditions. The default path does not repair malformed expressions or data.

## Model walkthroughs

| Scenario | Expected path | Evidence type |
| --- | --- | --- |
| Valid non-organic details | Validate, Yes, Organic claimed No, Publish | BPMN graph walkthrough plus evaluated Boolean conditions |
| Valid organic details and successful verifier | Validate, Yes, Organic claimed Yes, Check certification, Publish after verifier success | BPMN graph walkthrough plus evaluated Boolean conditions |
| Invalid details then corrected non-organic data | Validate, No, Request corrections, receive corrected message, validate again, Yes, No organic claim, Publish | BPMN graph walkthrough plus evaluated Boolean conditions |
| Repeated invalid submissions | Repeat correction loop until validation succeeds | BPMN graph walkthrough |
| Certification invalid or verifier unavailable | Certification job cannot complete successfully or permit publication. Taha Card 23 supplies final exception routes | Documented service contract and explicit handoff, pending implementation |

These results distinguish FEEL evaluation, model structure validation and graph walkthroughs as the lab requires. They do not demonstrate worker execution or a deployed Camunda instance.

## Teaching references

- `Week 10 - FEEL Expressions Technical Lab.docx`, Exercises 2, 4 and 5.
- `Week 8 Tutorial.docx`, Implement Mode and job-worker explanation.
- `Task 1 - Use Cases.pdf`, page 1.
