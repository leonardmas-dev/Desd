# Bristol Regional Food Network — Digital Marketplace
## Task 1: Stakeholder Analysis Matrix & Domain Business Rules

> **Module:** UFCFTR-30-3 Distributed & Enterprise Software Development (2026–27)  
> **Use Case:** **Use Case 1 — Producer Product Listing and Inventory Management**  
> **Document Leads:** Ahmed (Product Owner) & Yassen (Scrum Master)  
> **Traceability:** Aligns directly with [`strategic-enterprise.bpmn`](../bpmn/strategic-enterprise.bpmn)  

---

## 1. Executive Summary

This document formalises the **Socio-Technical Stakeholder Analysis** and **Domain Business Rules** for the Bristol Regional Food Network, specifically focused on **Use Case 1**. 

In accordance with enterprise modelling best practices, every task, gateway, and message flow in our BPMN models directly traces back to a requirement, constraint, or goal identified in this matrix.

---

## 2. Comprehensive Stakeholder Matrix

| Stakeholder | Category | Primary Goals in Use Case 1 | Key Constraints & Pain Points | BPMN Mapping (Pool / Element) |
| :--- | :--- | :--- | :--- | :--- |
| **Local Food Producers (SMEs)** *(Farms, Dairies, Bakeries)* | Primary Actor *(External Partner)* | • Quickly list seasonal produce without technical barriers.<br>• Update stock availability with minimal manual effort.<br>• Secure weekly payouts with transparent 5% fee deductions.<br>• Receive minimum 48h lead time on incoming orders. | • Low digital literacy (currently spend up to 15 hours/week on phone/email orders).<br>• Vulnerable to seasonal weather disruptions and rapid stock exhaustion.<br>• Cannot afford complex ERP or software licensing fees. | **Top Pool:** `Participant_Producer`<br>• `Flow_Msg_ListingSubmit`<br>• `Flow_Msg_Replenish`<br>• `Flow_Msg_Payout` |
| **Marketplace Operations & Administrator** | Process Owner *(Internal)* | • Maintain high catalogue data quality and regulatory compliance.<br>• Prevent overselling by automatically managing inventory states.<br>• Protect network reputation by enforcing organic validation.<br>• Automate 5% commission calculation and financial reporting. | • Manual administrative overhead of checking individual farmer claims is unscalable.<br>• Strict legal liability under UK food safety legislation. | **Central Pool:** `Participant_Marketplace`<br>• **Lane 1:** `Product & Inventory Management`<br>• **Lane 2:** `Order Processing & Settlement` |
| **External Organic Certifier** *(e.g. Soil Association UK)* | Secondary Actor *(External Regulatory Body)* | • Enforce organic standards compliance.<br>• Ensure certification licenses are authentic, active, and not expired.<br>• Protect consumers from fraudulent "greenwashing" claims. | • Relies on automated REST APIs; occasional network latency or maintenance outages must be handled gracefully without crashing the marketplace. | **Bottom-Left Pool:** `Participant_External`<br>• `Task_VerifyOrganic`<br>• `Flow_Msg_OrganicVerify`<br>• `Flow_Msg_OrganicResponse` |
| **Local Consumers** *(Families, Catering Groups, Restaurants)* | Consumer Actor *(External End-User)* | • Discover authentic, locally-grown food within a 20-mile radius.<br>• View transparent product details: harvest date, allergens, and food miles.<br>• Enjoy 100% stock fulfillment certainty (no post-checkout cancellations). | • Restricted time to visit physical farm shops during limited opening hours.<br>• Need clear allergen warnings (compliance with Natasha's Law). | **Bottom-Right Pool:** `Participant_Customer`<br>• `Flow_Msg_PublishAlert`<br>• `Flow_Msg_OrderPlacement` |
| **Payment Gateway Provider** *(Stripe Test Sandbox)* | Technology Partner *(External)* | • Provide PCI-DSS compliant payment tokenisation.<br>• Enable multi-party automated payouts to individual producer bank accounts. | • Must operate strictly in sandbox mode for academic development. | **Bottom-Left Pool:** `Participant_External`<br>• `Task_WeeklySettlement` |

---

## 3. Domain Business Rules (BR) Specification

The following business rules govern the logic executed within our BPMN processes:

### BR-01: Mandatory Product Information Validation
* **Rule Statement:** Every submitted product listing must include all mandatory fields:
  1. Product Name (Text, max 100 chars)
  2. Description & Category (`Vegetables`, `Dairy`, `Bakery`, `Preserves`, `Seasonal Specialities`)
  3. Unit Price (£ GBP)
  4. Available Stock Quantity (Integer $> 0$)
  5. Seasonal Availability Period (`StartDate` to `EndDate`)
  6. Farm Origin & Postcode (within 20-mile Bristol radius)
  7. Harvest Date (for fresh produce) or Best-Before Date (for preserves/dairy)
  8. Allergen Declarations (mandatory under Natasha's Law)
* **Enforcement:** `Task_ValidateMandatory` checks completeness. If any field is missing, gateway `Gateway_ValidInfo` redirects token to `Task_RequestCorrection`.

### BR-02: Organic Claim Verification
* **Rule Statement:** If a producer ticks `"Claim Organic Certification"`, the listing cannot be published until the certification license number is verified against the external Organic Certifier (Soil Association) API.
* **Exception Handling:**
  * If valid $\rightarrow$ product is tagged with the certified organic badge and published.
  * If invalid/expired $\rightarrow$ producer is notified, organic badge is denied, and listing is flagged.
  * If external API times out/is down $\rightarrow$ system retries with exponential back-off before routing to manual admin review.

### BR-03: Zero-Stock Automatic Unpublishing
* **Rule Statement:** When an order is placed and stock deduction causes inventory to reach exactly `0`, the system must **immediately and automatically unpublish** the product from the public catalogue.
* **Rationale:** Eliminates the risk of overselling and customer disappointment.
* **Enforcement:** `Gateway_StockDepleted` routes token to `Task_UnpublishZeroStock` and dispatches `Flow_Msg_RestockNotice` to the producer.

### BR-04: Seasonal Availability Window Verification
* **Rule Statement:** When a producer submits replenished stock, the system must check the current calendar date against the product's `Seasonal Availability Period`.
* **Enforcement:**
  * **Current Date $\le$ Season End Date:** Product is automatically republished to the live catalogue (`Flow_SeasonReopen`).
  * **Current Date $>$ Season End Date:** Product is retired to archive storage (`Task_ArchiveProduct`) until the next agricultural season.

### BR-05: Order Lead Time Guarantee
* **Rule Statement:** To accommodate smallholder harvesting and baking schedules, all order dispatches must enforce a minimum **48-hour preparation lead time**.
* **Enforcement:** Represented in message flow `Flow_Msg_OrderDispatchAlert`.

### BR-06: Revenue Share & Payout Settlement
* **Rule Statement:** The marketplace automatically calculates and retains a **5% platform commission** on gross sales. The remaining 95% is aggregated and settled weekly via Stripe directly into each producer's bank account.
* **Enforcement:** Modeled in `Task_WeeklySettlement` and `Flow_Msg_Payout`.

---

## 4. Requirements Traceability Matrix (BPMN Alignment)

| Business Rule | Case Study Requirement | Strategic BPMN Element ID | Operational Implementation Target |
| :--- | :--- | :--- | :--- |
| **BR-01** | Producer Product Management | `Task_ValidateMandatory`, `Gateway_ValidInfo` | Camunda Form Schema with validation constraints |
| **BR-02** | Quality & Organic Assurance | `Gateway_OrganicClaim`, `Task_VerifyOrganic` | Python/Node REST Mock Worker (`organic-verifier`) |
| **BR-03** | Real-time Inventory Depletion | `Gateway_StockDepleted`, `Task_UnpublishZeroStock` | Camunda Event Gateway & Catalogue DB Status |
| **BR-04** | Seasonal Produce Lifecycles | `Gateway_SeasonalCheck`, `Task_ArchiveProduct` | FEEL Expression Date Evaluation (`now() <= endDate`) |
| **BR-05** | Producer 48h Preparation SLA | `Flow_Msg_OrderDispatchAlert` | ISO 8601 Timer & Notification Service Task |
| **BR-06** | 5% Commission & Weekly Payout | `Task_WeeklySettlement`, `Flow_Msg_Payout` | Automated calculation formula & Stripe Sandbox API |

---

*Authored by Ahmed (Product Owner) & Yassen (Scrum Master)* 
*Reviewed and verified by:* Yassen (Scrum Master) - 19 Oct 2026 
*Bristol Regional Food Network — UFCFTR-30-3 Task 1*
