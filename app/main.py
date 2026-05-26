import os
from fastapi import FastAPI, HTTPException, Request, status
from app.services.gemini import GeminiAuditService
from google.cloud import bigquery
from google.auth.exceptions import DefaultCredentialsError

app = FastAPI(title="AegisMind Event-Driven Core")
gemini_service = GeminiAuditService()

try:
    bq_client = bigquery.Client()
except DefaultCredentialsError:
    print("WARNING: No GCP credentials found. BigQuery writes will be skipped locally.")
    bq_client = None

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/audit-trigger")
async def handle_gcs_event(request: Request):
    """
    Catches event notifications whenever a document drops inside the monitored GCS Bucket
    """
    headers = request.headers
    # Eventarc or standard storage notification verification
    if "ce-subject" not in headers and "X-Goog-Resource-State" not in headers:
        raise HTTPException(status_code=400, detail="Not a valid event notification request")
    
    body = await request.json()
    
    # Extract file details dynamically from the event body
    bucket_name = body.get("bucket")
    file_name = body.get("name")
    content_type = body.get("contentType", "application/pdf")
    
    if not bucket_name or not file_name:
        raise HTTPException(status_code=422, detail="Missing bucket name or file resource identifier")
        
    gcs_uri = f"gs://{bucket_name}/{file_name}"
    
    try:
        # Run Multimodal Inference Pipeline
        audit_result = await gemini_service.analyze_document_from_gcs(gcs_uri, content_type)
        
        # Save structured results to BigQuery
        table_id = os.getenv("BIGQUERY_TABLE_ID")
        if table_id and bq_client:
            row_to_insert = [audit_result.model_dump()]
            errors = bq_client.insert_rows_json(table_id, row_to_insert)
            if errors:
                print(f"BigQuery write logging errors encountered: {errors}")
        elif table_id and not bq_client:
            print("Skipping BigQuery write locally: No credentials found.")
                
        return {
            "status": "processed",
            "source_resource": gcs_uri,
            "data": audit_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")
