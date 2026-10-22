# Bristol Regional Food Network — Digital Marketplace
## Task 1: Selection & Justification of Two Major Functionalities

> *Module:* UFCFTR-30-3 Distributed & Enterprise Software Development (2026–27)  
> *Selected Use Case:* *Use Case 1 — Producer Product Listing and Inventory Management*  
> *Author:* Yaseen (Scrum Master)  
> *Reviewed & Approved by:* Ahmed (Product Owner)  
> *Status:* Agreed & Submitted for Sprint 1 Review  

---

## 1. Executive Context & Selection Rationale

The Bristol Regional Food Network connects 40 small-to-medium enterprise (SME) producers within a 20-mile radius of Bristol to local consumers, community groups, and restaurants. 

To satisfy the Task 1 assessment specification, our group has selected *Use Case 1 (Producer Product Listing and Inventory Management). In accordance with the assessment brief, this case has been decomposed into **two substantial, complementary, and end-to-end business functionalities*:

1. *Major Functionality A:* Product Submission, Validation & External Organic Certification
2. *Major Functionality B:* Dynamic Inventory Tracking & Seasonal Lifecycle Management

These two functionalities represent the two critical operational phases of a vendor's lifecycle on the marketplace: onboarding a product with full legal/quality compliance, and dynamically maintaining its stock and seasonal availability during live trading.

---

## 2. Detailed Specification: Major Functionality A
### Product Submission, Validation & External Organic Certification


[Start: Listing Submitted] 
       │
       ▼
(User Task: Validate Mandatory Data) ──[Invalid]──► (User Task: Request Correction) ──┐
       │                                                                              │
    [Valid]                                                                           │
       ▼                                                                              │
(Gateway: Organic Claimed?) ────[No]──────────────────────────────────────────────┐   │
       │                                                                          │   │
     [Yes]                                                                        │   │
       ▼                                                                          │   │
(Service Task: Verify Organic API) ──[API Down/Timeout]──► (Timer Retry / Admin)  │   │
       │                                                                          │   │
   [Verified]                                                                     │   │
       ▼                                                                          │   │
(Service Task: Publish Product to Live Catalogue) ◄───────────────────────────────┘   │
       │                                                                              │
       ▼                                                                              │
[End: Product Published]                                                              ◄


### A. Business Scope & Purpose
Enables a local SME producer to register a new food item, enforce strict data integrity and food safety laws (including Natasha’s Law allergen labelling and harvest date transparency), and automatically verify organic accreditation with an independent authority (Soil Association UK) prior to catalogue publication.

### B. Core Process Elements (Assessment Criteria Alignment)
* *User Interactions (Camunda Forms):*
  * ProductSubmissionForm: Captures product name, category, unit price, initial quantity, harvest date, best-before date, farm location postcode, allergen checklist (14 major allergens), and organic claim flag.
  * CorrectionRequestForm: Displays specific validation feedback to the producer when mandatory details are incomplete or malformed.
* *Automated Processing & Service Tasks:*
  * verify-organic-cert: REST API call to external mock Soil Association registry passing licence number and producer postcode.
  * publish-to-catalogue: Service worker updating the live product database status from PENDING_VERIFICATION to ACTIVE.
* *Business Decisions & Gateways:*
  * Gateway_ValidInfo (XOR): Determines whether all mandatory food safety fields meet regulatory schema.
  * Gateway_OrganicClaim (XOR): Routes listing to external API verification if organic status is claimed.
  * Gateway_CertStatus (XOR): Validates API response (VALID, INVALID, EXPIRED).
* *Alternative & Exceptional Flows:*
  * Validation Error Path: Loops back to producer with corrective prompts.
  * Invalid Certification: Rejects organic badge, notifies producer, and offers publication as non-organic standard produce or cancellation.
  * Service Failure / Timeout: Boundary timer event initiates automated exponential retry (up to 3 attempts) before escalating to manual admin review.

---

## 3. Detailed Specification: Major Functionality B
### Dynamic Inventory Tracking & Seasonal Lifecycle Management


[Message Start: Order Placed / Stock Deduction]
       │
       ▼
(Service Task: Deduct Stock Quantity)
       │
       ▼
(Gateway: Stock Level = 0?) ───[Stock > 0]───► [End: Stock Updated]
       │
    [Stock = 0]
       ▼
(Service Task: Automatically Unpublish Product from Catalogue)
       │
       ▼
(Message Flow: Dispatch Zero-Stock Alert to Producer)
       │
       ▼
(User Task: Producer Submits Stock Replenishment)
       │
       ▼
(Gateway: Within Seasonal Availability Date Range?)
       ├───[Current Date <= Season End]──► (Service Task: Republish to Catalogue) ──► [End]
       └───[Current Date > Season End]───► (Service Task: Archive Seasonal Product) ─► [End]


### A. Business Scope & Purpose
Prevents overselling by automatically tracking inventory depletion in real time, withdrawing exhausted items from the public marketplace, facilitating producer restock workflows, and auditing seasonal date cutoffs for fresh regional produce.

### B. Core Process Elements (Assessment Criteria Alignment)
* *User Interactions (Camunda Forms):*
  * ProducerRestockForm: Allows the producer to enter replenished quantity, updated harvest batch dates, and revised seasonal end dates without creating an entirely new listing.
* *Automated Processing & Service Tasks:*
  * deduct-inventory: Event-driven decrement of available quantity upon confirmed customer purchase.
  * unpublish-stock: Immediate status transition to OUT_OF_STOCK, hiding the product from consumer browse/search queries.
  * archive-seasonal-product: Retires items whose agricultural season has concluded, preserving transaction history while clearing the active catalogue.
* *Business Decisions & Gateways:*
  * Gateway_StockDepleted (XOR): Evaluates inventory threshold (stockQuantity == 0).
  * Gateway_SeasonalCheck (XOR): Evaluates date logic (currentDate <= seasonalEndDate) using Camunda FEEL expressions.
* *Alternative & Exceptional Flows:*
  * Zero-Stock Exception: Automatic unpublishing prevents multi-vendor basket conflicts.
  * Seasonal Expiration: If restock arrives after the regional season has ended (e.g. British strawberries in November), product is safely archived rather than erroneously republished.

---

## 4. Academic Justification Against Assessment Criteria

The module assessment brief requires that the two chosen functionalities:
> "should be sufficiently substantial to demonstrate an end-to-end business process and provide opportunities for user interaction, automated processing, business decisions, service interaction, data processing, and alternative or exceptional process flows."

Our two selected functionalities meet every dimension of this standard:

| Assessment Requirement | How Functionality A Fulfills It | How Functionality B Fulfills It |
| :--- | :--- | :--- |
| *User Interaction* | Custom Camunda Forms for listing submission and correction loops. | Producer restock and batch update tasklist forms. |
| *Automated Processing* | Automated data schema validation and live catalogue publishing. | Event-driven inventory deductions and automated status toggles. |
| *Business Decisions* | XOR gateways evaluating mandatory fields and organic status. | XOR gateways evaluating zero-stock triggers and seasonal date windows. |
| *Service Interaction* | External REST API integration with Soil Association UK. | Database catalogue status updates and inventory event streaming. |
| *Data Handling* | Manages rich payloads (harvest dates, allergens, postcodes, prices). | Manages numerical counters, date calculations, and stock flags. |
| *Exception Handling* | Soil Association API timeouts, retry timers, invalid certification fallbacks. | Zero-stock unpublishing, season-ended archival routing. |
| *Task 2 Readiness* | Directly maps to Django REST endpoints (/api/products/, /api/verify-organic/). | Directly maps to inventory microservices and Docker mock containers. |

---

## 5. Traceability to Assessment Deliverables


Use Case 1 (Specification)
   │
   ├──► i* Socio-Technical Models (SD & SR) ────────────► Captures Producer, Admin & Certifier Goals
   │
   ├──► Strategic Enterprise BPMN (`strategic-enterprise.bpmn`) ─► Maps overall 4-pool architecture
   │
   ├──► Operational BPMN #1 (Functionality A) ──────────► `op1-product-listing-validation.bpmn`
   │
   ├──► Operational BPMN #2 (Functionality B) ──────────► `op2-inventory-seasonal-lifecycle.bpmn`
   │
   └──► Camunda Executable Implementation ──────────────► Executable Zeebe processes with Forms & Workers


---

Authored by Yaseen (Scrum Master)  
Approved by Ahmed (Product Owner)  
Bristol Regional Food Network — UFCFTR-30-3 Task 1