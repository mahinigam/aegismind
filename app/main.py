import os
import json
from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from app.database import get_db, Job
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

from pydantic import BaseModel

class SubmitRequest(BaseModel):
    gcs_uri: str
    content_type: str = "application/pdf"

async def process_document_background(job_id: str, gcs_uri: str, content_type: str):
    db = next(get_db())
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
        
    job.status = "PROCESSING"
    db.commit()
    
    try:
        # Run Multimodal Inference Pipeline
        audit_result = await gemini_service.analyze_document_from_gcs(gcs_uri, content_type)
        
        job.status = "COMPLETED"
        job.result_json = audit_result.model_dump_json()
        db.commit()
        
        # Save structured results to BigQuery
        table_id = os.getenv("BIGQUERY_TABLE_ID")
        if table_id and bq_client:
            row_to_insert = [audit_result.model_dump()]
            errors = bq_client.insert_rows_json(table_id, row_to_insert)
            if errors:
                print(f"BigQuery write logging errors encountered: {errors}")
                
    except Exception as e:
        job.status = "FAILED"
        job.result_json = json.dumps({"error": str(e)})
        db.commit()

@app.post("/api/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(req: SubmitRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Submits a document for background async processing.
    """
    job = Job(status="PENDING")
    db.add(job)
    db.commit()
    db.refresh(job)
    
    background_tasks.add_task(process_document_background, job.id, req.gcs_uri, req.content_type)
    
    return {"job_id": job.id, "status": job.status}

@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Polls the current status of an async job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    response = {"job_id": job.id, "status": job.status}
    if job.result_json:
        try:
            response["result"] = json.loads(job.result_json)
        except:
            response["result"] = job.result_json
    return response

@app.post("/api/dlq-handler")
async def handle_dlq_event(request: Request):
    """
    Acts as a Dead Letter Queue (DLQ) handler for Pub/Sub push subscriptions.
    Logs and alerts on events that failed processing after multiple retries.
    """
    body = await request.json()
    message = body.get("message", {})
    attributes = message.get("attributes", {})
    
    print(f"🚨 [DLQ ALERT] Message failed processing 5+ times. Attributes: {attributes}")
    print(f"Message Data: {message.get('data')}")
    
    # In an enterprise system, this would trigger a PagerDuty alert or write to a dedicated DLQ BigQuery table.
    return {"status": "logged_to_dlq"}
