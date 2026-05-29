import os
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
from app.schemas.audit import FinancialAuditReport

class GeminiAuditService:
    def __init__(self):
        # Works via Google AI Studio API key or native Vertex AI service accounts
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"

    async def analyze_document_from_gcs(self, gcs_uri: str, mime_type: str) -> FinancialAuditReport:
        # Reference a remote file stored in GCS directly via Part block
        document_part = types.Part.from_uri(
            file_uri=gcs_uri,
            mime_type=mime_type
        )
        return await self._run_inference(document_part)

    async def analyze_document_from_bytes(self, file_bytes: bytes, mime_type: str) -> FinancialAuditReport:
        # For local testing without a GCS bucket
        document_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type
        )
        return await self._run_inference(document_part)

    async def _run_inference(self, document_part: types.Part) -> FinancialAuditReport:
        system_instruction = (
            "You are an expert Forensic Financial Auditor. Your task is to process incoming document pages, "
            "extract mathematical table listings, and check for accounting discrepancies, fraud, or anomalies. "
            "Crucially, if an error is found, return the precise 2D bounding boxes [ymin, xmin, ymax, xmax] "
            "on a 0-1000 normalized scale showing exactly where the textual mismatch exists."
        )

        prompt = (
            "Perform a strict compliance audit on this document. Extract items into structured rows. "
            "If any fraud or calculation mismatch is occurring, flag it immediately and provide the exact bounding boxes."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[document_part, prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                # Enforce JSON generation matching our strict Pydantic structure
                response_mime_type="application/json",
                response_schema=FinancialAuditReport,
                temperature=0.1
            )
        )
        
        # Returns parsed data fitting our exact schema validated object
        report = FinancialAuditReport.model_validate_json(response.text)
        
        # Calculate tokens and cost
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            metadata = response.usage_metadata
            prompt_tokens = metadata.prompt_token_count or 0
            completion_tokens = metadata.candidates_token_count or 0
            total_tokens = metadata.total_token_count or 0
            
            # Gemini 2.5 Flash Pricing
            # Input: $0.075 / 1M tokens
            # Output: $0.30 / 1M tokens
            cost = (prompt_tokens / 1_000_000 * 0.075) + (completion_tokens / 1_000_000 * 0.30)
            
            report.token_usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }
            report.inference_cost_usd = round(cost, 6)
            
        return report
