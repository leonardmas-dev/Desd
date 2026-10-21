# Legal, Ethical, Social, and Professional (LESP) Analysis

**Project:** Bristol Regional Food Network (BRFN) Digital Marketplace  
**Document:** `docs/lesp-evaluation.md`  
**Focus:** LESP Rules for Use Case 1 (Producer Product Listing & Inventory Management)  
**Author:** Thierno  

---

## 1. Introduction
Use Case 1 (Producer Product Listing and Inventory Management) involves handling food safety details, organic product claims, producer personal data, and public health alerts. This document explains the Legal, Ethical, Social, and Professional (LESP) rules that guide the marketplace to ensure legal compliance, fair operations, and alignment with the British Computer Society (BCS) Code of Conduct.

---

## 2. Legal Compliance Framework

### 2.1 Food Safety & Labelling Laws
* **Food Safety Act 1990:** Producers and the platform share legal responsibility to ensure that all listed food is safe to eat, accurately described, and not misleading.
* **Natasha's Law (Food Information Amendment 2021):** The product entry form forces producers to list all 14 major food allergens (such as nuts, gluten, and dairy). The system rejects any product submission if allergen details are missing.

### 2.2 Legal Liability & Platform Role
* **Shared Liability Model:** Producers are responsible for their product accuracy, but the platform acts as the online seller. To protect against legal risks, the system stores permanent audit records linking every product listing to the producer's account, creation time, and allergen declarations.
* **Product Traceability:** If a food safety recall happens, the database allows administrators to quickly identify affected products, producers, and customer orders.

### 2.3 Data Protection & Privacy (UK GDPR)
* **Data Minimisation:** The product entry form asks only for necessary business details needed for the product catalog and tax reporting (such as farm postcode, contact details, and bank payout information).
* **Privacy & Transparency:** Producer personal details are stored securely. Postcodes are used only to calculate the 20-mile delivery boundary and food miles without displaying private farm addresses online.

---

## 3. Ethical Standards & Design Choices

### 3.1 Preventing False Organic Claims 
* **Automatic Certificate Verification:** To protect buyers from false organic claims, any producer ticking "Certified Organic" must provide a valid licence number. The system checks this number against an official certifier database (such as the Soil Association UK).
* **Backup Error Rule:** If the verification checking system is offline or times out (503 error), the system does not give organic status by default. Instead, the item is published under a `PENDING_VERIFICATION` status without an organic badge until an admin reviews it.

### 3.2 Fair Platform Pricing & Small Business Protection
* **Fixed 5% Commission:** Platform fees are capped at a clear 5% commission. This ensures small local farms keep 95% of their sales to support their business.
* **No Overselling Penalties:** Automatic stock updates (hiding products when stock reaches 0) protect small producers from customer complaints or financial disputes caused by overselling.

---

## 4. Social Impact & Rural Tech Challenges

### 4.1 Supporting Rural Farmers with Low Tech Experience
* **Context:** Many of the 40 local food producers have limited experience with digital tools and may have slow internet access in rural areas.
* **Simple Form Design:** The Use Case 1 web form is designed to be very easy to use—featuring clear labels, simple date selectors, toggle switches, and minimal typing requirements.
* **Saving Working Time:** By streamlining product entry and stock updates, the system reduces the 15 hours per week producers currently spend taking manual orders over the phone or email.

---

## 5. Professional Standards & BCS Code of Conduct

Software developers working on the BRFN platform follow the four main pillars of the **British Computer Society (BCS) Code of Conduct**:

| BCS Code Pillar | How It Applies to Use Case 1 | Developer Responsibility |
| :--- | :--- | :--- |
| **1. Public Interest** | Required allergen warnings and food safety audit logs protect consumer health. | Make sure data validation rules cannot be bypassed in the website forms. |
| **2. Professional Competence** | Safe handling of external system failures (such as Organic Verification API downtime). | Write clean code with proper error handling and complete sandbox testing before launch. |
| **3. Duty to Relevant Authority** | Compliance with UK tax auditing rules, 5% fee transparency, and UK GDPR data privacy. | Keep clear documentation and respect user data boundaries. |
| **4. Duty to the Profession** | Honest, clear reporting of system capabilities and design decisions. | Maintain clean code repositories and follow proper GitHub version control habits. |

---