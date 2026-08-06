import os
# pyrefly: ignore [missing-import]
from PIL import Image, ImageDraw, ImageFont

def create_fraudulent_invoice():
    # Create a blank white image
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # Try to load a default font, or fallback to the basic one
    try:
        # Depending on OS, Arial might not be available, but let's try a default
        font_large = ImageFont.truetype("Arial.ttf", 36)
        font_medium = ImageFont.truetype("Arial.ttf", 24)
        font_small = ImageFont.truetype("Arial.ttf", 18)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Define text colors
    text_color = (0, 0, 0)
    
    # Header
    draw.text((50, 50), "ACME CORP - INVOICE", fill=text_color, font=font_large)
    draw.text((50, 100), "Invoice #: 99402", fill=text_color, font=font_medium)
    draw.text((50, 130), "Date: 2026-08-06", fill=text_color, font=font_medium)
    draw.text((50, 160), "Bill To: AegisMind LLC", fill=text_color, font=font_medium)
    
    # Table Header
    y_offset = 250
    draw.line((50, y_offset, 750, y_offset), fill=text_color, width=2)
    draw.text((50, y_offset + 10), "Description", fill=text_color, font=font_medium)
    draw.text((600, y_offset + 10), "Amount", fill=text_color, font=font_medium)
    draw.line((50, y_offset + 40, 750, y_offset + 40), fill=text_color, width=2)
    
    # Table Items
    items = [
        ("Cloud Infrastructure (Q3)", "$ 4,500.00"),
        ("Database Licensing", "$ 1,200.00"),
        ("Security Audit Services", "$ 2,300.00")
    ]
    
    y_offset += 60
    for desc, amt in items:
        draw.text((50, y_offset), desc, fill=text_color, font=font_medium)
        draw.text((600, y_offset), amt, fill=text_color, font=font_medium)
        y_offset += 40
        
    draw.line((50, y_offset, 750, y_offset), fill=text_color, width=2)
    
    # Deliberate Mathematical Error (4500 + 1200 + 2300 = 8000)
    # We will state the subtotal is 12,000 to trigger the AI fraud detection
    y_offset += 20
    draw.text((450, y_offset), "Subtotal:", fill=text_color, font=font_medium)
    draw.text((600, y_offset), "$ 12,000.00", fill=text_color, font=font_medium)
    
    y_offset += 40
    draw.text((450, y_offset), "Tax (10%):", fill=text_color, font=font_medium)
    draw.text((600, y_offset), "$ 1,200.00", fill=text_color, font=font_medium)
    
    y_offset += 50
    draw.line((450, y_offset, 750, y_offset), fill=text_color, width=3)
    
    y_offset += 10
    draw.text((450, y_offset), "TOTAL DUE:", fill=text_color, font=font_large)
    draw.text((600, y_offset), "$ 13,200.00", fill=(200, 0, 0), font=font_large) # Highlighted slightly in red
    
    # Save as PDF
    pdf_path = os.path.join(os.getcwd(), "fraud_test_invoice.pdf")
    image.save(pdf_path, "PDF", resolution=100.0)
    print(f"Generated test invoice with intentional math errors: {pdf_path}")

if __name__ == "__main__":
    create_fraudulent_invoice()
