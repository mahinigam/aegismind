import streamlit as st
import json
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image, ImageDraw
import sys
import os
import asyncio

# Add parent directory to path so we can import our services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.gemini import GeminiAuditService

st.set_page_config(page_title="AegisMind Review", layout="wide")

st.title("AegisMind: Human-in-the-Loop Review UI")
st.markdown("Upload a document to run the Gemini 2.5 Flash audit pipeline, visualize grounding coordinates, and approve/reject anomalies.")

@st.cache_resource
def get_service():
    return GeminiAuditService()

uploaded_file = st.file_uploader("Upload Document for Audit", type=["pdf", "png", "jpg"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    mime_type = uploaded_file.type
    
    # Render UI Layout
    col1, col2 = st.columns([1, 1])
    
    with st.spinner("Gemini 2.5 Flash is analyzing the document..."):
        service = get_service()
        # Streamlit is synchronous, but our service is async. We run it in an event loop.
        report = asyncio.run(service.analyze_document_from_bytes(file_bytes, mime_type))
        
    with col1:
        st.subheader("Document Viewer")
        if mime_type == "application/pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            # Group bounding boxes by page
            bboxes_by_page = {}
            if report.is_financial_document and report.is_anomaly_detected and report.visual_grounding_coordinates:
                for bbox in report.visual_grounding_coordinates:
                    pnum = getattr(bbox, "page_number", 0)
                    bboxes_by_page.setdefault(pnum, []).append(bbox)
            else:
                bboxes_by_page[0] = []
                
            for page_num in sorted(bboxes_by_page.keys()):
                if page_num >= len(doc):
                    page_num = len(doc) - 1
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                bboxes = bboxes_by_page[page_num]
                if bboxes:
                    draw = ImageDraw.Draw(img)
                    for bbox in bboxes:
                        coords = bbox.box_2d
                        y_min = (coords[0] / 1000.0) * img.height
                        x_min = (coords[1] / 1000.0) * img.width
                        y_max = (coords[2] / 1000.0) * img.height
                        x_max = (coords[3] / 1000.0) * img.width
                        
                        # Add padding and use thinner, semi-transparent border (alpha ignored if not RGBA but 2 is thinner)
                        pad = 4
                        draw.rectangle([x_min - pad, y_min - pad, x_max + pad, y_max + pad], outline="red", width=2)
                        
                        # Draw badge background for text
                        text_x = x_min
                        text_y = max(0, y_min - 15 - pad)
                        try:
                            left, top, right, bottom = draw.textbbox((text_x, text_y), bbox.label)
                            draw.rectangle([left - 2, top - 2, right + 2, bottom + 2], fill="red")
                        except AttributeError:
                            # Fallback if textbbox not supported
                            pass
                        draw.text((text_x, text_y), bbox.label, fill="white")
                
                st.write(f"**Page {page_num + 1}**")
                st.image(img, use_container_width=True)
        else:
            # Handle standard image uploads similarly
            img = Image.open(BytesIO(file_bytes))
            if report.is_financial_document and report.is_anomaly_detected and report.visual_grounding_coordinates:
                draw = ImageDraw.Draw(img)
                for bbox in report.visual_grounding_coordinates:
                    coords = bbox.box_2d
                    y_min = (coords[0] / 1000.0) * img.height
                    x_min = (coords[1] / 1000.0) * img.width
                    y_max = (coords[2] / 1000.0) * img.height
                    x_max = (coords[3] / 1000.0) * img.width
                    
                    pad = 4
                    draw.rectangle([x_min - pad, y_min - pad, x_max + pad, y_max + pad], outline="red", width=2)
                    
                    text_x = x_min
                    text_y = max(0, y_min - 15 - pad)
                    try:
                        left, top, right, bottom = draw.textbbox((text_x, text_y), bbox.label)
                        draw.rectangle([left - 2, top - 2, right + 2, bottom + 2], fill="red")
                    except AttributeError:
                        pass
                    draw.text((text_x, text_y), bbox.label, fill="white")
            st.image(img, use_container_width=True)
            
    with col2:
        st.subheader("Audit Results")
        
        if not getattr(report, "is_financial_document", True):
            st.warning(f"⚠️ Non-Financial Document Detected: {report.document_type}")
            st.write("This document was rejected because it does not appear to be a financial record (invoice, ledger, receipt, etc.). AegisMind is designed strictly to audit financial calculations.")
            
            st.write("### AI Economics")
            st.metric(label="Inference Cost", value=f"${report.inference_cost_usd:.5f}")
            st.json(report.token_usage)
        else:
            if report.is_anomaly_detected:
                st.error("🚨 FRAUD / ANOMALY DETECTED")
                if report.audit_justification:
                    st.markdown("### Anomaly Breakdown")
                    st.info(f"**Finding:** {report.audit_justification.finding}")
                    
                    col_a, col_b = st.columns(2)
                    col_a.metric("Actual Value (On Document)", report.audit_justification.actual_value)
                    col_b.metric("Expected Value (Calculated)", report.audit_justification.expected_value)
                    
                    st.warning(f"**Recommendation:** {report.audit_justification.recommendation}")
                else:
                    st.write("**Justification**: Anomaly detected but no details provided.")
            else:
                st.success("✅ Clean Document")
                
            st.write("### Extracted Financial Tables")
            formatted_tables = []
            for t in report.extracted_tables:
                formatted_tables.append({
                    "Item Description": t.item_description,
                    "Amount": f"${t.amount:,.2f}",
                    "Confidence": f"{t.confidence_score:.2%}"
                })
            st.table(formatted_tables)
            
            st.write("### AI Economics")
            st.metric(label="Inference Cost", value=f"${report.inference_cost_usd:.5f}")
            st.json(report.token_usage)
            
            st.write("### Human Action")
            if st.button("Approve & Finalize"):
                st.success("Report Approved! Sent back to data warehouse.")
            if st.button("Reject (Flag for Manual Review)"):
                st.warning("Report Rejected! Escalated to Compliance Team.")
