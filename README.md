#Enterprise AI Invoice Processing & Validation Platform

Enterprise-inspired Intelligent Document Processing (IDP) platform for AI-powered invoice extraction, validation, and human review using Azure Document Intelligence and GPT-4o-mini.

Business Problem

Finance teams spend significant time manually downloading invoices, extracting financial information, validating totals, and entering data into ERP systems. While OCR reduces manual effort, it cannot reliably understand business context or validate extracted information.

This project combines Azure Document Intelligence with GPT-based extraction and validation to automate the early stages of invoice processing while preserving auditability and human oversight.

Key Features

Email-based invoice ingestion

AI document classification (Invoice / Purchase Order / GoodsReceipt)

Azure Document Intelligence OCR

GPT-powered invoice extraction

AI-assisted validation with hallucination guardrails

SHA-256 duplicate document detection

SQLite persistence layer

Processing audit trail

Human review dashboard (Streamlit)

Modular architecture for future ERP integration

System Architecture

Replace with images/architecture.png

Email Inbox
     │
     ▼
Email Agent
     │
     ▼
Classification Agent
     │
     ▼
Workflow Orchestrator
     │
     ▼
Azure Document Intelligence
     │
     ▼
AI Extraction Agent
     │
     ▼
AI Validation Agent
     │
     ▼
Storage Layer (SQLite)
     │
     ▼
Repository Layer
     │
     ▼
Streamlit Dashboard

Processing Workflow

Download invoice attachments from email.

Classify documents (Invoice / PO / GRN).

Register the document and compute a SHA-256 hash.

Extract text and tables using Azure Document Intelligence.

Convert OCR output into structured invoice JSON using GPT.

Validate extracted information using a dedicated validation agent.

Persist OCR, extracted, and validated results into SQLite.

Review invoices through the Streamlit dashboard.

Enterprise Design Decisions

Decision                                Reason

Azure Document Intelligence             Accurate OCR and tableextraction

Separate Extraction & Validation        Reduces hallucinations andimproves reliability

GPT-4o-mini                             Semantic understanding offinancial documents

SHA-256 Hashing                         Prevents duplicate documentprocessing

Repository Pattern                      Separates persistence fromretrieval logic

SQLite                                  Lightweight database withfuture migration path

Audit Logging                           Complete document traceability

Technology Stack

Component       Technology

Language        PythonOCR             Azure Document IntelligenceAI              OpenAI GPT-4o-miniDatabase        SQLiteDashboard       StreamlitEmail           IMAPConfiguration   python-dotenv

Business Applications

Suitable for organizations processing supplier invoices including:

Manufacturing

Third-Party Logistics (3PL)

Distribution

Retail

Healthcare

Construction

Accounting Firms

Shared Service Centers

Current Scope: Intelligent invoice processing and validation.Purchase Order matching, Goods Receipt matching, and three-wayreconciliation are future enhancements.

Project Structure

enterprise-ai-invoice-processing/
│
├── azure_invoice_ocr.py
├── classify_agent.py
├── email_agent.py
├── extractor_agent.py
├── Orchestrator.py
├── storage_agent.py
├── validator_agent.py
├── ui_app.py
│
├── sample_invoice_1.pdf
├── sample_invoice_2.pdf
├── sample_invoice_3.pdf
│
├── images/
│   ├── architecture.png
│   ├── workflow.png
│   ├── dashboard_success.png
│   ├── dashboard_review.png
│   └── database_schema.png
│
├── README.md
├── requirements.txt
├── .env.example
└── LICENSE

Dashboard

Replace with screenshots:

images/dashboard_success.png

images/dashboard_review.png

Getting Started

Install Dependencies

pip install -r requirements.txt

Configure Environment

Create a .env file:

OPENAI_API_KEY=
AZURE_FORMREC_ENDPOINT=
AZURE_FORMREC_KEY=
EMAIL_USER=
EMAIL_PASS=
EMAIL_HOST=

Run Processing

python Orchestrator.py

Launch Dashboard

streamlit run ui_app.py

Future Roadmap

Purchase Order matching

Goods Receipt processing

Three-way invoice matching

SAP ERP integration

REST API (FastAPI)

PostgreSQL migration

Azure cloud deployment

Multi-language support

Multi-currency validation

License

This project is intended for educational, research, and portfoliopurposes.

Author Notes

This project demonstrates a modular approach to Intelligent DocumentProcessing by combining enterprise OCR, AI-driven extraction,deterministic validation, persistent storage, and a human reviewworkflow. The architecture emphasizes maintainability, traceability, andextensibility rather than relying on a single end-to-end AI model.
