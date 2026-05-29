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
            # Render first page of PDF to image
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Draw bounding boxes if anomaly detected
            if report.is_anomaly_detected and report.visual_grounding_coordinates:
                draw = ImageDraw.Draw(img)
                for bbox in report.visual_grounding_coordinates:
                    coords = bbox.box_2d
                    # Coordinates are 0-1000 normalized, convert to image scale
                    y_min = (coords[0] / 1000.0) * img.height
                    x_min = (coords[1] / 1000.0) * img.width
                    y_max = (coords[2] / 1000.0) * img.height
                    x_max = (coords[3] / 1000.0) * img.width
                    
                    # Draw a thick red box
                    draw.rectangle([x_min, y_min, x_max, y_max], outline="red", width=4)
                    # Optionally, add a label above it
                    draw.text((x_min, max(0, y_min - 15)), bbox.label, fill="red")
            
            st.image(img, use_container_width=True)
        else:
            # Handle standard image uploads similarly
            img = Image.open(BytesIO(file_bytes))
            if report.is_anomaly_detected and report.visual_grounding_coordinates:
                draw = ImageDraw.Draw(img)
                for bbox in report.visual_grounding_coordinates:
                    coords = bbox.box_2d
                    y_min = (coords[0] / 1000.0) * img.height
                    x_min = (coords[1] / 1000.0) * img.width
                    y_max = (coords[2] / 1000.0) * img.height
                    x_max = (coords[3] / 1000.0) * img.width
                    draw.rectangle([x_min, y_min, x_max, y_max], outline="red", width=4)
            st.image(img, use_container_width=True)
            
    with col2:
        st.subheader("Audit Results")
        if report.is_anomaly_detected:
            st.error("🚨 FRAUD / ANOMALY DETECTED")
            st.write(f"**Justification**: {report.audit_justification}")
        else:
            st.success("✅ Clean Document")
            
        st.write("### Extracted Financial Tables")
        st.table([t.model_dump() for t in report.extracted_tables])
        
        st.write("### AI Economics")
        st.metric(label="Inference Cost", value=f"${report.inference_cost_usd:.5f}")
        st.json(report.token_usage)
        
        st.write("### Human Action")
        if st.button("Approve & Finalize"):
            st.success("Report Approved! Sent back to data warehouse.")
        if st.button("Reject (Flag for Manual Review)"):
            st.warning("Report Rejected! Escalated to Compliance Team.")
