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
Yassen	Product Owner	Developer	Scrum Master
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
1	i* Socio-Technical Model (SD & SR Diagrams)	🟡 In Progress	/diagrams
2	Strategic-Level Business Process Model (BPMN)	🟡 In Progress	/bpmn/strategic-enterprise.bpmn
3	Selection & Justification of 2 Major Functionalities	🟢 Complete	/docs/functionalities-justification.md
4	End-to-End Operational BPMN Models (×2)	🟡 In Progress	/bpmn/
5	Camunda Process Automation (Executable BPMN, Forms, Service Tasks)	🔴 Planned	/camunda/
6	LESP Evaluation (Legal, Ethical, Social, Professional)	🟡 In Progress	/docs/lesp-evaluation.md
7	Signed Contribution Matrix	🔴 Planned	/docs/contribution-matrix.md
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