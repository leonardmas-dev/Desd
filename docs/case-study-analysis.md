# Case Study Domain analysis and producer profiles
**Project:** Bristol Regional Food Network (BRFN) Digital Marketplace  
**Document:** `docs/case-study-analysis.md`  
**Focus:** Use Case 1 Domain Analysis & Operational Constraints  
**Authors:** Taha & Thierno

The Bristol Regional Food Network (BRFN) connects 40 small-to-medium enterprise (SME) producers with local consumers within a 20-mile radius of Bristol city centre. 
The primary objective of the digital marketplace is to lower administrative barriers, streamline inventory management, and expand market access across three distinct customer segments while operating under strict operational, seasonal, and compliance constraints.

## 2. Producer Capability & Operational Profile *(Taha)*






## 3. Customer Segment Analysis & Purchasing Barriers *(Thierno)*
Market research identifies three main customer groups in the Bristol area. The website design directly solves their main shopping problems:

| Customer Group | What They Need | Main Shopping Problems | System Solution (Use Case 1) |
| :--- | :--- | :--- | :--- |
| **1. Young Families & Professionals** | Fresh local food; convenient shopping. | Farm shops have short opening hours; driving to multiple farms takes too long. | One online shop, clear harvest dates, single shopping basket, and home delivery options. |
| **2. Community Groups & Caterers** | Bulk supplies; reliable delivery schedules for schools and care homes. | Hard to find reliable local food suppliers quickly. | Clear live stock levels, best-before dates, and bulk food categories. |
| **3. Cafés & Restaurants** | High-quality local ingredients; clear farm origins for their menus. | Managing separate orders and invoices with many small farms takes too much time. | All orders combined in one cart with a single invoice and payout system. |





## 4. Supply Chain & Geographic Boundaries *(Taha)*





## 5. Operational Business Rules for Use Case 1 *(Thierno)*
1. **48-Hour Lead Time:** The system enforces a **48-hour order cutoff**. Products listed must reflect stock that can be prepared within this time.
2. **Automatic Stock Rules:**
   - **AVAILABLE:** Quantity is greater than 0 AND current date is inside the season window.
   - **UNAVAILABLE_OUT_OF_STOCK:** Quantity reaches 0 AND current date is inside the season window.
   - **EXPIRED_OFF_SEASON:** Current date is outside the season window.
3. **Marketplace Fee:** The system automatically calculates and keeps a **5% commission** on total sales before sending weekly payouts to producers.
4. **Organic Certificate Check:** Products claimed as organic must be checked against an external verification system. If the checking system is down or times out (503 error), the product is marked as `PENDING_VERIFICATION` and sent for manual admin review so the producer can still finish submitting their product.  









