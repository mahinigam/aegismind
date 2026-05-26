# AegisMind

An end-to-end serverless, event-driven multimodal document forensic audit pipeline on Google Cloud Platform (GCP).

## Architecture

1. **Ingestion**: A user uploads an unstructured multi-page document to GCS.
2. **Event Triggering**: GCS emits a finalized object event which triggers an Eventarc to Cloud Run.
3. **Serverless Orchestration**: FastAPI inside Cloud Run catches payload, streams file from GCS, calls Google GenAI SDK.
4. **Multimodal Inference**: `gemini-2.5-flash` model extracts tabular data deterministically into JSON, flags anomalies, outputs visual bounding boxes.
5. **Analytics Sink**: Structured audit trail is streamed natively into Google BigQuery.
