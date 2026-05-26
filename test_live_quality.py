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

async def main():
    if not os.getenv("GEMINI_API_KEY"):
        console.print("[bold red]❌ Error:[/bold red] You must set the GEMINI_API_KEY environment variable to test result quality locally.")
        console.print("Get one for free at: [blue]https://aistudio.google.com/app/apikey[/blue]")
        console.print("Run this script using: [bold]GEMINI_API_KEY='your_api_key' python test_live_quality.py \\[optional_pdf_file][/bold]")
        return

    console.print("[bold cyan]🚀 Initializing Gemini Service...[/bold cyan]")
    service = GeminiAuditService()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        console.print(f"[bold yellow]📄 Loading document from {file_path}...[/bold yellow]")
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
        console.print("[bold yellow]📝 Creating a dummy financial document in memory...[/bold yellow]")
        # This simulates a document with an intentional mathematical fraud (500 + 200 != 900)
        document_bytes = b"INVOICE\nItem 1: $500\nItem 2: $200\nTotal: $900\n" 
        mime_type = "text/plain"
    
    console.print("[bold magenta]🧠 Sending to Gemini 2.5 Flash for Forensic Audit...[/bold magenta]\n")
    try:
        report = await service.analyze_document_from_bytes(document_bytes, mime_type)
        
        console.print(Panel.fit("[bold green]✅ Extraction Complete! Structured Output:[/bold green]"))
        
        # Display the tables extracted using Rich Table
        table = Table(title="Extracted Financial Items", show_header=True, header_style="bold cyan")
        table.add_column("Item Description", style="dim")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Confidence", justify="right", style="yellow")
        
        for item in report.extracted_tables:
            table.add_row(item.item_description, f"${item.amount:,.2f}", f"{item.confidence_score:.2f}")
        
        console.print(table)
        console.print("\n")
        
        # Display the Raw JSON nicely
        console.print("[bold]Raw JSON Output:[/bold]")
        console.print(JSON(report.model_dump_json()))
        console.print("\n")
        
        if report.is_anomaly_detected:
            coord_str = "\n".join([f"• [bold]{bbox.label}[/bold]: {bbox.box_2d}" for bbox in report.visual_grounding_coordinates])
            
            panel_content = Text("🚨 FRAUD DETECTED!\n\n", style="bold red")
            panel_content.append("Justification:\n", style="bold white")
            panel_content.append(report.audit_justification + "\n\n", style="red")
            panel_content.append("Visual Coordinates:\n", style="bold white")
            panel_content.append(coord_str, style="yellow")
            
            console.print(Panel(panel_content, border_style="red", title="[bold red]Forensic Audit Result[/bold red]"))
        else:
            console.print(Panel("[bold green]✅ No anomalies detected. Document is clean.[/bold green]", border_style="green"))
            
    except Exception as e:
        console.print(f"[bold red]Error during inference: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())
