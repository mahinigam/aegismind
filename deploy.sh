#!/bin/bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION="asia-south1" # Bengaluru / Mumbai region data clusters
export BUCKET_NAME="$PROJECT_ID-aegismind-ingest"
export SERVICE_NAME="aegismind-core"
export DATASET_NAME="aegismind_analytics"
export TABLE_NAME="audit_records"

echo "1. Enabling Cloud Build, Cloud Run, Eventarc, BigQuery, and Vertex AI APIs..."
gcloud services enable run.googleapis.com build.googleapis.com eventarc.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com

echo "2. Setting up Google Cloud Storage Bucket..."
gcloud storage buckets create gs://$BUCKET_NAME --location=$REGION

echo "3. Initializing BigQuery Dataset..."
gcloud bq datasets create --location=$REGION $DATASET_NAME

echo "4. Deploying Serverless Code Engine to Cloud Run (scales down to 0 instances when idle)..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --allow-unauthenticated \
  --set-env-vars BIGQUERY_TABLE_ID="$PROJECT_ID.$DATASET_NAME.$TABLE_NAME"

echo "5. Connecting Eventarc Trigger from Storage Ingest bucket directly to the Cloud Run Microservice endpoint..."
gcloud eventarc triggers create aegismind-gcs-trigger \
  --location=$REGION \
  --destination-run-service=$SERVICE_NAME \
  --destination-run-path="/api/audit-trigger" \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --event-filters="bucket=$BUCKET_NAME" \
  --service-account="$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com"

echo "Deployment complete! Upload any document to gs://$BUCKET_NAME to see it audit live!"
