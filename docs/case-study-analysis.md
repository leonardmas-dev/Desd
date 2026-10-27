# Case Study Domain Analysis and Producer Profiles
**Project:** Bristol Regional Food Network (BRFN) Digital Marketplace  
**Document:** `docs/case-study-analysis.md`  
**Focus:** Use Case 1 Domain Analysis & Operational Constraints  
**Authors:** Taha & Thierno

## 1. Domain Overview
The Bristol Regional Food Network (BRFN) connects 40 small-to-medium enterprise (SME) producers with local consumers within a 20-mile radius of Bristol city centre. 
The primary objective of the digital marketplace is to lower administrative barriers, streamline inventory management, and expand market access across three distinct customer segments while operating under strict operational, seasonal, and compliance constraints.

## 2. Producer Capability & Operational Profile *(Taha)*
The 40 producers are independent SMEs, not BRFN staff, so the platform cannot assume their tools, skills or working hours. Use Case 1 must fit how they already work.

| Area | Current situation | Implication for Use Case 1 |
| :--- | :--- | :--- |
| **Digital literacy** | Low | Product submission must be a short, simple web form with plain-language labels and error messages that explain how to fix the problem. |
| **Current workflow** | Manual phone and email handling, about 15 hours per week | This is the baseline the system must reduce. Listing and stock updates move online. The reduction target is to be agreed with the tutor. |
| **Order lead time** | 48 hours needed to prepare orders | Enforced by the system as a cutoff (see Section 5, rule 1). |
| **Devices and connectivity** | Not assessed; assumed basic devices and variable connectivity | The form should work on mobile and cope with a slow connection. |

**Requirements derived from the producer profile**

- **F:** A producer can submit product data (harvest date, allergens, best-before date, price, availability) through a web form.
- **NF (usability):** A producer with no training can list a product without assistance. The completion-time target is to be agreed with the tutor.
- **NF (business rule):** Orders respect the 48-hour lead time.
- **Constraint:** No installed software or technical skills may be assumed of producers.

## 3. Customer Segment Analysis & Purchasing Barriers *(Thierno)*
Market research identifies three main customer groups in the Bristol area. The website design directly solves their main shopping problems:

| Customer Group | What They Need | Main Shopping Problems | System Solution (Use Case 1) |
| :--- | :--- | :--- | :--- |
| **1. Young Families & Professionals** | Fresh local food; convenient shopping. | Farm shops have short opening hours; driving to multiple farms takes too long. | One online shop, clear harvest dates, single shopping basket, and home delivery options. |
| **2. Community Groups & Caterers** | Bulk supplies; reliable delivery schedules for schools and care homes. | Hard to find reliable local food suppliers quickly. | Clear live stock levels, best-before dates, and bulk food categories. |
| **3. Cafés & Restaurants** | High-quality local ingredients; clear farm origins for their menus. | Managing separate orders and invoices with many small farms takes too much time. | All orders combined in one cart with a single invoice and payout system. |

## 4. Supply Chain & Geographic Boundaries *(Taha)*

| Boundary | Detail | Effect on the system |
| :--- | :--- | :--- |
| **Geography** | Producers must be within a 20-mile radius of Bristol. | Eligibility check at onboarding (e.g. by postcode). Producers outside the radius are rejected. |
| **Product categories** | [ADD category list from the case study] | Categories drive the listing form fields and the bulk-buy filter for caterers. |
| **Seasonality** | Produce has seasonal lifecycles. | Each product carries a season window, which drives the AVAILABLE and EXPIRED_OFF_SEASON states in Section 5. |
| **Commission** | 5% platform commission on sales. | Calculated automatically before weekly payouts (Section 5, rule 3). |

**Forces that justify a distributed design (Week 8):** ownership (independent producers), geography (20-mile local network), scale (seasonal demand peaks) and failure isolation (the external organic certification API can time out without stopping product submission).

## 5. Operational Business Rules for Use Case 1 *(Thierno)*
1. **48-Hour Lead Time:** The system enforces a **48-hour order cutoff**. Products listed must reflect stock that can be prepared within this time.
2. **Automatic Stock Rules:**
   - **AVAILABLE:** Quantity is greater than 0 AND current date is inside the season window.
   - **UNAVAILABLE_OUT_OF_STOCK:** Quantity reaches 0 AND current date is inside the season window.
   - **EXPIRED_OFF_SEASON:** Current date is outside the season window.
3. **Marketplace Fee:** The system automatically calculates and keeps a **5% commission** on total sales before sending weekly payouts to producers.
4. **Organic Certificate Check:** Products claimed as organic must be checked against an external verification system. If the checking system is down or times out (503 error), the product is marked as `PENDING_VERIFICATION` and sent for manual admin review so the producer can still finish submitting their product.
