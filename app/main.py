import os
import json
from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Depends, UploadFile, File
from fastapi.responses import Response
from app.database import get_db, Job
from app.services.gemini import GeminiAuditService
from google.cloud import bigquery
from google.cloud import storage
from google.cloud.firestore import Query
from google.auth.exceptions import DefaultCredentialsError

app = FastAPI(title="AegisMind Event-Driven Core")

# Initialize gemini_service gracefully if API key is missing during startup
try:
    gemini_service = GeminiAuditService()
except ValueError as e:
    print(f"WARNING: Gemini service initialization failed: {e}")
    gemini_service = None

try:
    bq_client = bigquery.Client()
except DefaultCredentialsError:
    print("WARNING: Default credentials not found. BigQuery logging will be disabled.")
    bq_client = None

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Eventarc webhook implementation
@app.post("/api/audit-trigger")
async def audit_trigger(request: Request):
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
        if not gemini_service:
            raise Exception("Gemini service is not initialized. Please configure GEMINI_API_KEY.")
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
    doc_ref = db.collection("jobs").document(job_id)
    doc = doc_ref.get()
    if not doc.exists:
        return
        
    job = Job.from_dict(doc.to_dict())
    job.status = "PROCESSING"
    doc_ref.set(job.to_dict())
    
    try:
        # Run Multimodal Inference Pipeline
        if not gemini_service:
            raise Exception("Gemini service is not initialized. Please configure GEMINI_API_KEY.")
        audit_result = await gemini_service.analyze_document_from_gcs(gcs_uri, content_type)
        
        job.status = "COMPLETED"
        job.result_json = audit_result.model_dump_json()
        doc_ref.set(job.to_dict())
        
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
        doc_ref.set(job.to_dict())

@app.post("/api/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_job(req: SubmitRequest, background_tasks: BackgroundTasks, db = Depends(get_db)):
    """
    Submits a document for background async processing.
    """
    job = Job(status="PENDING")
    db.collection("jobs").document(job.id).set(job.to_dict())
    
    background_tasks.add_task(process_document_background, job.id, req.gcs_uri, req.content_type)
    
    return {"job_id": job.id, "status": job.status}

@app.post("/api/upload-local", status_code=status.HTTP_202_ACCEPTED)
async def submit_local_job(background_tasks: BackgroundTasks, file: UploadFile = File(...), db = Depends(get_db)):
    """
    Uploads file to GCS and queues the background job via Firestore.
    """
    job = Job(status="PENDING")
    db.collection("jobs").document(job.id).set(job.to_dict())
    
    file_bytes = await file.read()
    
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        # Fallback to local processing if GCS bucket is not configured
        job.status = "FAILED"
        job.result_json = json.dumps({"error": "GCS_BUCKET_NAME is not set."})
        db.collection("jobs").document(job.id).set(job.to_dict())
        return {"job_id": job.id, "status": job.status}
        
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(f"uploads/{job.id}.pdf")
        blob.upload_from_string(file_bytes, content_type=file.content_type)
    except Exception as e:
        job.status = "FAILED"
        job.result_json = json.dumps({"error": f"Failed to upload to GCS: {str(e)}"})
        db.collection("jobs").document(job.id).set(job.to_dict())
        return {"job_id": job.id, "status": job.status}
        
    gcs_uri = f"gs://{bucket_name}/uploads/{job.id}.pdf"
    background_tasks.add_task(process_document_background, job.id, gcs_uri, file.content_type)
    
    return {"job_id": job.id, "status": job.status}

@app.get("/api/download/{job_id}")
async def download_file(job_id: str):
    """
    Fetches original document from GCS for Visual Grounding in UI.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME env var not set")
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(f"uploads/{job_id}.pdf")
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found in GCS")
        file_bytes = blob.download_as_bytes()
        return Response(content=file_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found or error: {str(e)}")

@app.get("/api/jobs")
async def get_jobs(db = Depends(get_db)):
    """
    Retrieves all jobs for the review queue.
    """
    docs = db.collection("jobs").order_by("created_at", direction=Query.DESCENDING).get()
    results = []
    for doc in docs:
        job = Job.from_dict(doc.to_dict())
        job_data = {"job_id": job.id, "status": job.status, "created_at": job.created_at.isoformat() if hasattr(job.created_at, 'isoformat') else str(job.created_at)}
        if job.result_json:
            try:
                parsed_result = json.loads(job.result_json)
                job_data["is_anomaly_detected"] = parsed_result.get("is_anomaly_detected", False)
                job_data["document_type"] = parsed_result.get("document_type", "Unknown")
            except:
                pass
        results.append(job_data)
    return results

@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str, db = Depends(get_db)):
    """
    Polls the current status of an async job.
    """
    doc = db.collection("jobs").document(job_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = Job.from_dict(doc.to_dict())
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
    
    return {"status": "logged_to_dlq"}
