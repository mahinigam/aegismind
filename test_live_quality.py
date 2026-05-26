import os
import sys
import asyncio
from app.services.gemini import GeminiAuditService

# Import rich components
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON
from rich.text import Text

console = Console()

# ANSI Escape Codes for raw terminal styling
ANSI_RESET = "\033[0m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_CYAN = "\033[96m"
ANSI_BOLD = "\033[1m"

async def main():
    if not os.getenv("GEMINI_API_KEY"):
        print(f"{ANSI_BOLD}{ANSI_RED}[ERROR]{ANSI_RESET} You must set the GEMINI_API_KEY environment variable to test result quality locally.")
        print("Get one for free at: https://aistudio.google.com/app/apikey")
        print("Run this script using: GEMINI_API_KEY='your_api_key' python test_live_quality.py [optional_pdf_file]")
        return

    print(f"{ANSI_BOLD}{ANSI_CYAN}[SYSTEM]{ANSI_RESET} Initializing Gemini Service...")
    service = GeminiAuditService()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"{ANSI_BOLD}{ANSI_YELLOW}[INPUT]{ANSI_RESET} Loading document from {file_path}...")
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
        print(f"{ANSI_BOLD}{ANSI_YELLOW}[INPUT]{ANSI_RESET} Creating a dummy financial document in memory...")
        # This simulates a document with an intentional mathematical fraud (500 + 200 != 900)
        document_bytes = b"INVOICE\nItem 1: $500\nItem 2: $200\nTotal: $900\n" 
        mime_type = "text/plain"
    
    print(f"{ANSI_BOLD}{ANSI_CYAN}[PROCESS]{ANSI_RESET} Sending to Gemini 2.5 Flash for Forensic Audit...\n")
    try:
        report = await service.analyze_document_from_bytes(document_bytes, mime_type)
        
        console.print(Panel.fit("[bold green][SUCCESS] Extraction Complete! Structured Output:[/bold green]"))
        
        # Display the tables extracted using Rich Table
        table = Table(title="Extracted Financial Items", show_header=True, header_style="bold cyan")
        table.add_column("Item Description", style="dim")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Confidence", justify="right", style="yellow")
        
        for item in report.extracted_tables:
            table.add_row(item.item_description, f"${item.amount:,.2f}", f"{item.confidence_score:.2f}")
        
        console.print(table)
        print("\n")
        
        # Display the Raw JSON nicely
        print(f"{ANSI_BOLD}Raw JSON Output:{ANSI_RESET}")
        console.print(JSON(report.model_dump_json()))
        print("\n")
        
        if report.is_anomaly_detected:
            coord_str = "\n".join([f"* [bold]{bbox.label}[/bold]: {bbox.box_2d}" for bbox in report.visual_grounding_coordinates])
            
            panel_content = Text("[ALERT] FRAUD DETECTED!\n\n", style="bold red")
            panel_content.append("Justification:\n", style="bold white")
            panel_content.append(report.audit_justification + "\n\n", style="red")
            panel_content.append("Visual Coordinates:\n", style="bold white")
            panel_content.append(coord_str, style="yellow")
            
            console.print(Panel(panel_content, border_style="red", title="[bold red]Forensic Audit Result[/bold red]"))
        else:
            console.print(Panel("[bold green][CLEAN] No anomalies detected. Document is clean.[/bold green]", border_style="green"))
            
    except Exception as e:
        print(f"{ANSI_BOLD}{ANSI_RED}[ERROR]{ANSI_RESET} Error during inference: {e}")

if __name__ == "__main__":
    asyncio.run(main())
