# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class AnomalyDetails(BaseModel):
    finding: str = Field(..., description="A detailed explanation of the math errors found.")
    expected_value: str = Field(..., description="A comma-separated list of the correct values, e.g., 'Subtotal: $8,000.00, Tax: $800.00, Total: $8,800.00'")
    actual_value: str = Field(..., description="A comma-separated list of the incorrect values found on the document, e.g., 'Subtotal: $12,000.00, Tax: $1,200.00, Total: $13,200.00'")
    recommendation: str = Field(..., description="Recommended action to resolve the anomaly")

class BoundingBox(BaseModel):
    box_2d: List[int] = Field(..., description="Normalized coordinates [ymin, xmin, ymax, xmax] scaled 0-1000")
    label: str = Field(..., description="Short identification label of what is highlighted")
    page_number: int = Field(..., description="The 0-indexed page number where this bounding box is located")

class TableRow(BaseModel):
    item_description: str
    amount: float
    confidence_score: float

class FinancialAuditReport(BaseModel):
    is_financial_document: bool = Field(..., description="True if the document is a financial record (invoice, receipt, ledger, etc.). False if it is a non-financial document like a job posting.")
    document_type: str = Field(..., description="Invoice, Tax Return, Bank Statement, Job Advertisement, etc.")
    extracted_tables: List[TableRow]
    is_anomaly_detected: bool = Field(..., description="True if fraud, calculations mismatch, or policy violation found")
    audit_justification: Optional[AnomalyDetails] = Field(None, description="Detailed structured reasoning if an anomaly is detected.")
    visual_grounding_coordinates: List[BoundingBox] = Field(..., description="Array of bounding boxes pointing directly to text discrepancies")

class FinancialAuditResult(FinancialAuditReport):
    inference_cost_usd: float = Field(0.0, description="The cost of this inference based on Gemini token usage")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Detailed prompt and completion token counts")
