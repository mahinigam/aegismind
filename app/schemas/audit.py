# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class BoundingBox(BaseModel):
    box_2d: List[int] = Field(..., description="Normalized coordinates [ymin, xmin, ymax, xmax] scaled 0-1000")
    label: str = Field(..., description="Short identification label of what is highlighted")

class TableRow(BaseModel):
    item_description: str
    amount: float
    confidence_score: float

class FinancialAuditReport(BaseModel):
    document_type: str = Field(..., description="Invoice, Tax Return, Bank Statement etc.")
    extracted_tables: List[TableRow]
    is_anomaly_detected: bool = Field(..., description="True if fraud, calculations mismatch, or policy violation found")
    audit_justification: str = Field(..., description="Chain of thought natural language reasoning behind anomaly status")
    visual_grounding_coordinates: List[BoundingBox] = Field(..., description="Array of bounding boxes pointing directly to text discrepancies")
    inference_cost_usd: float = Field(0.0, description="The cost of this inference based on Gemini token usage")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Detailed prompt and completion token counts")
