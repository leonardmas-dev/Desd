UFCFTR-30-3 — Distributed & Enterprise Software Development
Task 1: Socio-Technical Modelling, BPMN & Process Automation

University: UWE Bristol
Module: UFCFTR-30-3 Distributed & Enterprise Software Development (2026–27)
Case Study: Bristol Regional Food Network — Digital Marketplace
Selected Use Case: Use Case 1 — Producer Product Listing and Inventory Management
Submission Deadline: 10th December 2026, 14:00 (via GitHub repository)

👥 Team Members & Sprint Roles
Name	Sprint 1 (Strategic & Setup)	Sprint 2 (Operational & Initial Automation)	Sprint 3 (Integration & Demo)
Ahmed	Scrum Master	Developer	Developer
Yaseen	Product Owner	Developer	Scrum Master
Taha	Developer	Product Owner	Developer
Leonard	Developer	Scrum Master	Developer
Thierno	Developer	Developer	Product Owner
📌 Project Overview: Bristol Regional Food Network

The Bristol Regional Food Network is a digital marketplace connecting 40 local small-to-medium food producers (within a 20-mile radius of Bristol) with local consumers, community groups, and restaurants.

Our team is responsible for end-to-end analysis, modeling, and automated execution of Use Case 1: Producer Product Listing and Inventory Management.

🎯 The Two Agreed Major Functionalities:

Functionality A (Operational BPMN #1): Product Submission, Validation & External Organic Certification

Producer submits product data (harvest date, allergens, best-before date, pricing, availability).
System performs automated and human validation of mandatory fields with feedback loops.
External simulated API integration for Organic Certification Verification (e.g., Soil Association API).
Robust exception handling for service timeouts, network downtime, and invalid certifications.
Automatic publication to the live marketplace catalogue.

Functionality B (Operational BPMN #2): Dynamic Inventory Tracking & Seasonal Lifecycle Management

Automated inventory deduction upon order placement.
Zero-stock trigger that automatically unpublishes items to prevent overselling.
Restock & replenishment submission by producers.
Verification of quantity and seasonal availability windows before republishing.
Automated archival of expired seasonal produce.
📋 Task 1 Assessed Deliverables

Note: Per the assessment brief, there is no written report. Assessment is based on the auditable GitHub repository evidence and live in-class sprint demonstrations + Q&A.

#	Deliverable	Status	Location in Repo
1	i* Socio-Technical Model (SD & SR Diagrams)	🟡 In Progress	/diagrams (SR softgoals completed)
2	Strategic-Level Business Process Model (BPMN)	🟡 In Progress	/bpmn/strategic-enterprise.bpmn
3	Selection & Justification of 2 Major Functionalities	🟢 Complete	/docs/functionalities-justification.md
4	End-to-End Operational BPMN Models (×2)	🟡 In Progress	/bpmn/
5	Camunda Process Automation (Executable BPMN, Forms, Service Tasks)	🔴 Planned	/camunda/
6	LESP Evaluation (Legal, Ethical, Social, Professional)	🟡 In Progress	/docs/lesp-evaluation.md
7	Signed Contribution Matrix	🔴 Planned	/docs/contribution-matrix.md

## Taha's completed tasks

The following work was completed for the BPMN 1 operational model and the i* SR model.

### 1. Added the external organic certification interaction

The product-listing process now models certification as an interaction with an external verification service rather than as an unexplained internal step.

- Added an external **Organic Certification Verification Service** participant/pool.
- Added a separate external certification process with a message-start event, verification task, result task and end event.
- Replaced the internal certification service task with the `Task_VerifyCertification` call activity.
- Connected the marketplace process to the external process using explicit BPMN message flows.
- Added the `Organic certification check` request message.
- Added the `Certification verification result` response message.
- Kept the service boundary visible so the model shows which work is performed by the marketplace and which work is performed externally.

Main source file: [`models/validation.bpmn`](models/validation.bpmn).

### 2. Added certification decision and invalid-certification handling

After the certification result is received, the process now checks the result before the product can be published.

- Added the `Gateway_CertificationValid` exclusive gateway.
- The valid path continues to product publication.
- The invalid path goes to `Task_RejectCertification`.
- Added `End_CertificationRejected` so an invalid certification cannot reach the publication step.
- Used the `certificationValid = true` condition for the publication route.
- Used the invalid/default route for products whose claimed certification is rejected.

This makes the business rule explicit: a product with an invalid organic claim must not be published.

### 3. Added service-unavailable exception handling

The certification call activity now has an explicit failure route for an unavailable verification service.

- Added `Boundary_ServiceUnavailable` to the certification call activity.
- Used the `CERTIFICATION_SERVICE_UNAVAILABLE` error condition.
- Added `Task_HandleServiceUnavailable` for the marketplace response.
- Added `End_ServiceUnavailable` so the product is not published when verification cannot be completed.

This covers service downtime, timeout-like failures and unavailable external verification without silently treating the certification as valid.

### 4. Added SR-only softgoals and contribution links

The i* SR model now includes two quality objectives that explain why the operational controls matter:

- **Customer trust:** supported by successful certification verification and controlled product publication.
- **Data quality:** supported by product-detail validation/correction and certification verification.

The following positive contribution links were added:

- Certification verification → **Customer trust** (`make`).
- Product publication after checks → **Customer trust** (`make`).
- Product validation/correction → **Data quality** (`make`).
- Certification verification → **Data quality** (`help`).

These softgoals were intentionally added to the SR model only. The SD model was not changed.

The editable model is [`diagrams/istar-sr-marketplace.json`](diagrams/istar-sr-marketplace.json). The piStar upload copy is [`diagrams/goalModel.txt`](diagrams/goalModel.txt).

#### How to read the SR model

Read the model from the marketplace system outward:

1. **Marketplace System** is the main actor responsible for listing and inventory work.
2. The system's main goal is to keep products listed accurately and available.
3. The system decomposes that goal into product validation, certification verification, availability management and publication tasks.
4. **Customer trust** is the quality outcome supported by checking certifications and publishing only after the required checks pass.
5. **Data quality** is the quality outcome supported by validating product details, requesting corrections and checking certification information.
6. The arrows labelled `make` show a strong positive contribution. The arrow labelled `help` shows a supporting contribution.

The SR model therefore connects **what the system does** to **the quality it is expected to provide**. It does not describe the BPMN sequence itself; the detailed sequence and exception paths are in [`models/validation.bpmn`](models/validation.bpmn).

### 5. Made the SR model upload-compatible with piStar

The original SR source used hand-written identifiers that the online piStar loader rejected. The model was updated so that:

- Elements and links use UUID-shaped identifiers.
- All `source`, `target` and display references point to the updated identifiers.
- Contribution links use piStar's supported `label` values (`make` and `help`).
- The JSON remains syntactically valid and preserves the model contents and softgoals.

The `.txt` upload file contains the same JSON model contents. The extension is required only because the current online piStar file picker rejects the `.json` file type.

### 6. Documentation and verification completed

- Documented the BPMN certification interaction and exception paths.
- Documented the SR softgoals and their contribution links.
- Added piStar loading and PNG export instructions.
- Checked that the SR JSON parses successfully.
- Checked that the BPMN XML and cross-references remain valid.
- Checked that the i* link endpoints resolve to existing model elements.
- Ran `git diff --check` to verify clean patch formatting.

### Loading the SR model in piStar

The model is stored as JSON in [`diagrams/istar-sr-marketplace.json`](diagrams/istar-sr-marketplace.json). A ready-to-upload text copy is provided at [`diagrams/goalModel.txt`](diagrams/goalModel.txt). The current piStar web tool accepts the model contents only when the upload is treated as a text file, so if it reports **“Sorry, this kind of file is not valid”** for the `.json` file:

1. Use `goalModel.txt`, or make a copy of `istar-sr-marketplace.json`.
2. If making a copy, rename it to `istar-sr-marketplace.txt` (do not change its contents).
3. Open the [piStar tool](https://www.cin.ufpe.br/~jhcp/pistar/tool/).
4. Choose **File → Load Model**, select the `.txt` copy, and choose **Load model**.
5. Confirm that **Customer trust** and **Data quality** are visible in the SR diagram.
6. To create an updated image, choose **File → Save Image**, then select PNG.

The `.txt` extension is only a workaround for piStar's file-type check; the file contents remain valid JSON.

### Final result

The completed work now provides:

- A BPMN process that requests external certification, receives a result and makes a clear valid/invalid decision.
- A safe failure route when the external service is unavailable.
- An SR model that explains how validation, certification and publication improve customer trust and data quality.
- Traceable links between the BPMN activities and the corresponding SR tasks.
- A piStar-compatible text model that can be loaded and exported as a new image.

The rendered BPMN/i* exports should be regenerated in the relevant modelling tools after opening the updated source files.
📅 Sprint Schedule & Assessment Milestones
Sprint	Milestone Focus	Weighting	Target Review Date
Sprint 1	Strategic Process Analysis, Enterprise BPMN & Project Setup	20%	22nd October 2026
Sprint 2	i* SD/SR Models, 2 Operational BPMNs, Initial Camunda Execution	30%	2nd November 2026
Sprint 3	Final Camunda Automation, Forms, Service Tasks, Live Demonstration	50%	23rd November 2026
Final Repo Submission	Final repository audit and code freeze	—	10th December 2026 (14:00)

Assessment Structure:

80% Group Project Mark: Calculated from Sprints 1, 2, and 3, scaled by individual repository contributions and the signed Contribution Matrix.
20% Individual Stand-up Performance: Best 6 out of 9 in-person practical lab stand-ups.
🗂️ Repository Structure
/
├── README.md                                # Project overview, architecture, and team roles
├── .gitignore                               # Environment, OS, and cache ignore rules
├── /bpmn                                    # BPMN source files (.bpmn) and exported SVG/PNG
│   ├── strategic-enterprise.bpmn
│   ├── op1-product-listing-validation.bpmn
│   └── op2-inventory-seasonal-lifecycle.bpmn
├── /camunda                                 # Executable Camunda assets
│   ├── /forms                               # Camunda JSON form definitions
│   │   ├── product-submission-form.form
│   │   └── restock-form.form
│   └── /service-workers                     # Mock service scripts (Node.js/Python)
│       ├── organic-verifier-mock.py
│       └── catalogue-publisher.py
├── /diagrams                                # i* models and architecture diagrams
│   ├── istar-sd-model.png
│   ├── istar-sr-model.png
│   └── architecture-overview.png
└── /docs                                    # Project documentation and analysis
    ├── functionalities-justification.md
    ├── lesp-evaluation.md
    ├── requirements-traceability-matrix.md
    └── contribution-matrix.md
🛠️ Tools & Technologies
Tool	Purpose
Camunda Web Modeler & Desktop Modeler	BPMN 2.0 modeling, XML linting, executable attribute settings
Camunda 8 SaaS / Local Camunda Engine	Process orchestration, Zeebe engine execution, tasklist management
draw.io / iStar 2.0 Tool	Socio-technical i* SD and SR diagrams
Python / FastAPI / Docker	Simulated mock services (Organic verification API & Stripe sandbox)
Git / GitHub	Team version control, sprint issue tracking, audit trail
🔄 How We Work (Scrum Workflow)

We manage development through our Trello board:

⚡ Sprint Backlog: Current sprint tasks awaiting execution.
🔄 In Progress: Actively assigned tasks (max 1–2 per person).
👀 Review: Completed artefacts undergoing peer verification / syntax validation.
✅ Done: Committed to main repo with clean audit history.