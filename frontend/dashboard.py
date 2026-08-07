import streamlit as st
import json
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image, ImageDraw
import sys
import os
import time
import requests

# Add parent directory to path so we can import our schemas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.schemas.audit import FinancialAuditResult

st.set_page_config(page_title="AegisMind Review", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Upload Document", "Review Queue", "Analytics"])

API_BASE_URL = "http://localhost:8000"

def render_document(file_bytes, mime_type, report: FinancialAuditResult):
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
            
            st.write(f"**Page {page_num + 1}**")
            st.image(img, use_container_width=True)
    else:
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

def render_audit_results(report: FinancialAuditResult):
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

if page == "Upload Document":
    st.title("AegisMind: Upload Document")
    st.markdown("Upload a document to trigger the event-driven Gemini pipeline.")
    
    uploaded_file = st.file_uploader("Upload Document for Audit", type=["pdf", "png", "jpg"])
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        mime_type = uploaded_file.type
        
        col1, col2 = st.columns([1, 1])
        
        job_id = None
        
        with st.spinner("Submitting document to API..."):
            try:
                files = {"file": (uploaded_file.name, file_bytes, mime_type)}
                res = requests.post(f"{API_BASE_URL}/api/upload-local", files=files)
                res.raise_for_status()
                job_id = res.json().get("job_id")
            except Exception as e:
                st.error(f"Failed to submit to backend: {e}")
                
        if job_id:
            st.info(f"Job submitted! Job ID: {job_id}")
            report_data = None
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Polling loop
            while True:
                try:
                    status_res = requests.get(f"{API_BASE_URL}/api/status/{job_id}")
                    status_res.raise_for_status()
                    job_info = status_res.json()
                    
                    status_text.text(f"Status: {job_info['status']}")
                    
                    if job_info["status"] == "COMPLETED":
                        progress_bar.progress(100)
                        report_data = job_info["result"]
                        break
                    elif job_info["status"] == "FAILED":
                        progress_bar.progress(100)
                        st.error(f"Job failed: {job_info.get('result')}")
                        break
                    else:
                        time.sleep(2)
                except Exception as e:
                    st.error(f"Failed to poll backend: {e}")
                    break
                    
            if report_data:
                # Convert dict to Pydantic object
                report = FinancialAuditResult(**report_data)
                
                with col1:
                    render_document(file_bytes, mime_type, report)
                with col2:
                    render_audit_results(report)

elif page == "Review Queue":
    st.title("Review Queue")
    st.markdown("View all background-processed documents that require human attention.")
    
    try:
        res = requests.get(f"{API_BASE_URL}/api/jobs")
        res.raise_for_status()
        jobs = res.json()
        
        if not jobs:
            st.info("No jobs found in the queue.")
        else:
            st.write(f"Found {len(jobs)} total jobs.")
            
            # Show a simple table
            queue_data = []
            for j in jobs:
                queue_data.append({
                    "Job ID": j["job_id"],
                    "Status": j["status"],
                    "Type": j.get("document_type", "Unknown"),
                    "Anomaly": j.get("is_anomaly_detected", False),
                    "Created At": j["created_at"]
                })
            st.dataframe(queue_data)
            
            st.markdown("---")
            st.subheader("Inspect a Job")
            job_ids = [j["job_id"] for j in jobs if j["status"] == "COMPLETED"]
            selected_job = st.selectbox("Select a completed job to review", job_ids)
            
            if selected_job:
                job_res = requests.get(f"{API_BASE_URL}/api/status/{selected_job}")
                if job_res.status_code == 200:
                    job_info = job_res.json()
                    if job_info["status"] == "COMPLETED" and "result" in job_info:
                        report = FinancialAuditResult(**job_info["result"])
                        
                        col1, col2 = st.columns([1, 1])
                        
                        # Try to load local file if it exists
                        file_path = f"uploads/{selected_job}.pdf"
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                file_bytes = f.read()
                            with col1:
                                render_document(file_bytes, "application/pdf", report)
                        else:
                            with col1:
                                st.info("Original document not available locally.")
                                st.json(job_info["result"])
                                
                        with col2:
                            render_audit_results(report)
    except Exception as e:
        st.error(f"Could not connect to API: {e}")

elif page == "Analytics":
    st.title("AegisMind Analytics Dashboard")
    st.markdown("Monitor AI economics and inference costs across all processed documents.")
    
    try:
        res = requests.get(f"{API_BASE_URL}/api/jobs")
        res.raise_for_status()
        jobs = res.json()
        
        completed_jobs = [j for j in jobs if j["status"] == "COMPLETED" and "result" in j and j["result"]]
        
        if not completed_jobs:
            st.info("No completed jobs with data available yet.")
        else:
            total_cost = 0.0
            total_tokens = 0
            
            cost_timeline = {}
            
            for j in completed_jobs:
                report = j["result"]
                cost = report.get("inference_cost_usd", 0.0)
                tokens = report.get("token_usage", {}).get("total_tokens", 0)
                
                total_cost += cost
                total_tokens += tokens
                
                # Group by date for simple timeline
                date_str = j["created_at"].split("T")[0]
                cost_timeline[date_str] = cost_timeline.get(date_str, 0.0) + cost
                
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Completed Audits", len(completed_jobs))
            col2.metric("Total Inference Cost", f"${total_cost:.5f}")
            col3.metric("Total Tokens Processed", f"{total_tokens:,}")
            
            st.subheader("Inference Cost Over Time (USD)")
            st.bar_chart(cost_timeline)
            
    except Exception as e:
        st.error(f"Could not connect to API: {e}")
