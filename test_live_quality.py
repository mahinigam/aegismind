import os
import sys
import asyncio
from app.services.gemini import GeminiAuditService

async def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: You must set the GEMINI_API_KEY environment variable to test result quality locally.")
        print("Get one for free at: https://aistudio.google.com/app/apikey")
        print("Run this script using: GEMINI_API_KEY='your_api_key' python test_live_quality.py [optional_pdf_file]")
        return

    print("🚀 Initializing Gemini Service...")
    service = GeminiAuditService()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"📄 Loading document from {file_path}...")
        with open(file_path, "rb") as f:
            document_bytes = f.read()
        
        # Determine mime type from extension
        if file_path.lower().endswith(".pdf"):
            mime_type = "application/pdf"
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg")):
            mime_type = "image/jpeg"
        else:
            mime_type = "text/plain"
    else:
        print("📝 Creating a dummy financial document in memory...")
        # This simulates a document with an intentional mathematical fraud (500 + 200 != 900)
        document_bytes = b"INVOICE\nItem 1: $500\nItem 2: $200\nTotal: $900\n" 
        mime_type = "text/plain"
    
    print("🧠 Sending to Gemini 2.5 Flash for Forensic Audit...")
    try:
        report = await service.analyze_document_from_bytes(document_bytes, mime_type)
        print("\n✅ Extraction Complete! Here is the structured JSON output:\n")
        print(report.model_dump_json(indent=2))
        
        if report.is_anomaly_detected:
            print("\n🚨 FRAUD DETECTED! Justification:")
            print(report.audit_justification)
            print("Visual Coordinates:", report.visual_grounding_coordinates)
        else:
            print("\n✅ No anomalies detected.")
            
    except Exception as e:
        print(f"Error during inference: {e}")

if __name__ == "__main__":
    asyncio.run(main())
