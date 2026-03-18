from fpdf import FPDF
import os
import sys

# Setup FPDF
pdf = FPDF()
pdf.add_page()

font_path = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
try:
    # Adding a TrueType font in fpdf2 enables uharfbuzz text shaping automatically!
    pdf.add_font("Deva", style="", fname=font_path, uni=True)
    pdf.set_font("Deva", size=20)
    pdf.cell(100, 10, text="हिन्दी आणि मराठी अनुवाद", border=1, ln=1)
    
    # We can also draw strings at an absolute x, y
    pdf.set_font("Deva", size=15)
    # fpdf2 coordinate system is top-left, x from left, y from top
    pdf.text(x=50, y=100, text="वर्ल्डडॉक - क्लाउड बेस्ड डॉक्युमेंट ट्रान्सलेशन")
    
    pdf.output("test_fpdf2.pdf")
    print("SUCCESS: test_fpdf2.pdf generated!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
