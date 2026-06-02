# AegisMind

Serverless Multimodal Document Intelligence & Auditing Pipeline.

AegisMind is an event-driven AI platform built on Google Cloud Platform (GCP). It extracts semantic structure and audits unstructured financial and legal documents with high precision and zero runtime idle costs.

## Core Features

- **Automated Forensic Auditing**: Analyzes complex math and detects logic/policy violations across multi-page documents.
- **Explainable AI (XAI)**: Provides explicit visual grounding via bounding boxes mapping model reasoning back to exact document pages.
- **Multimodal Inference**: Leverages Gemini 2.5 Flash to process text, structural charts, and tables in parallel.
- **Deterministic Output**: Uses strict Pydantic schemas enforced by the Google GenAI SDK for predictable downstream processing.
- **Human-in-the-Loop Validation**: Includes a Streamlit dashboard for manual review of AI-flagged anomalies and financial economics tracking.
- **Resilient Architecture**: Incorporates asynchronous background processing, SQL job tracking, and Pub/Sub Dead Letter Queues (DLQ) for fault tolerance.

## Architecture

1. **Ingestion**: Documents are uploaded to Google Cloud Storage (GCS).
2. **Event Trigger**: GCS emits finalized object events, triggering Eventarc.
3. **Orchestration**: A containerized FastAPI service on Cloud Run processes payloads asynchronously.
4. **Analysis**: Gemini 2.5 Flash extracts data, calculates inference economics, and generates spatial grounding coordinates.
5. **Review Sink**: Outputs are tracked via SQLAlchemy/SQLite and available for Human-in-the-Loop review via the Streamlit dashboard.

## Tech Stack

- **Core**: Python, FastAPI, Pydantic, SQLAlchemy
- **AI/ML**: Google GenAI SDK, Gemini 2.5 Flash
- **Frontend**: Streamlit, PyMuPDF, Pillow
- **Infrastructure**: GCP (Cloud Run, GCS, Eventarc, Pub/Sub)
- **Tooling**: `uv` (Dependency Management)

## Local Development

```bash
# 1. Install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 2. Configure Environment
export GEMINI_API_KEY="your_api_key_here"

# 3. Launch Services
# Run the FastAPI backend
uvicorn app.main:app --reload

# Run the Human-in-the-Loop Dashboard
streamlit run frontend/dashboard.py

# 4. Testing & Evals
# Run the evaluation suite against the chaos test ledger
python evals/run_evals.py
```
