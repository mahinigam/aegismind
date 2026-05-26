# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.schemas.audit import FinancialAuditReport, TableRow, BoundingBox

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
@patch("app.services.gemini.GeminiAuditService.analyze_document_from_gcs", new_callable=AsyncMock)
def test_audit_trigger_success(mock_analyze):
    # Mock the Gemini response
    mock_analyze.return_value = FinancialAuditReport(
        document_type="Invoice",
        extracted_tables=[
            TableRow(item_description="Server Costs", amount=150.0, confidence_score=0.99)
        ],
        is_anomaly_detected=False,
        audit_justification="All calculations match.",
        visual_grounding_coordinates=[]
    )

    headers = {
        "ce-subject": "test-file.pdf"
    }
    payload = {
        "bucket": "test-bucket",
        "name": "test-file.pdf",
        "contentType": "application/pdf"
    }
    
    response = client.post("/api/audit-trigger", json=payload, headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "processed"
    assert data["source_resource"] == "gs://test-bucket/test-file.pdf"
    assert data["data"]["document_type"] == "Invoice"
    
    mock_analyze.assert_called_once_with("gs://test-bucket/test-file.pdf", "application/pdf")
