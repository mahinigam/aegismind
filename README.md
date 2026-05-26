# AegisMind

Serverless Multimodal Document Intelligence & Auditing Pipeline.

AegisMind is an event-driven AI pipeline built on Google Cloud Platform (GCP). It automatically extracts semantic structure and audits unstructured financial and legal documents with zero runtime idle costs.

## Features

- **Automated Forensic Auditing**: Analyzes complex math and detects logic/policy violations across multi-page documents.
- **Multimodal Inference**: Leverages Gemini 2.5 Flash to process text, structural charts, and tables in parallel.
- **Explainable AI (XAI)**: Provides visual grounding, mapping model reasoning back to source document bounding boxes.
- **Deterministic Output**: Uses Pydantic to enforce strict JSON schemas for predictable downstream processing.

## Architecture

1. **Ingestion**: Unstructured documents are uploaded to Google Cloud Storage (GCS).
2. **Event Trigger**: GCS emits a finalized object event, triggering Eventarc.
3. **Orchestration**: A containerized FastAPI service on Cloud Run processes the payload and invokes the Google GenAI SDK.
4. **Analysis**: Gemini 2.5 Flash extracts data, flags anomalies, and generates visual grounding coordinates.
5. **Data Sink**: The structured forensic audit trail is streamed to BigQuery for high-throughput anomaly analysis.

## Tech Stack

- **Core**: Python, FastAPI, Pydantic
- **AI/ML**: Google GenAI SDK, Gemini 2.5 Flash
- **Infrastructure**: GCP (Cloud Run, GCS, Eventarc, BigQuery)
- **Tooling**: `uv` (Dependency Management), Docker, Rich (CLI UI)

## Local Development

Test the pipeline's inference and reasoning engine locally.

```bash
# 1. Install dependencies via uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 2. Set your API Key
export GEMINI_API_KEY="your_api_key_here"

# 3. Run the live quality tester
python test_live_quality.py path/to/document.pdf
```
