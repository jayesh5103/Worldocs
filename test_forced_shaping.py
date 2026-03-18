from fpdf import FPDF
import os
import sys

try:
    pdf = FPDF()
    pdf.add_page()
    font_path = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'

    # Enable text shaping globally to ensure it throws an error if uharfbuzz is missing
    pdf.set_text_shaping(True)
    pdf.add_font("Deva", fname=font_path)
    pdf.set_font("Deva", size=20)

    text = "वर्ल्डडॉक - क्लाउड बेस्ड डॉक्युमेंट ट्रान्सलेशन प्रणाली"
    
    pdf.text(x=50, y=100, text=text)

    pdf.output("test_forced_shaping.pdf")
    print("SUCCESS: test_forced_shaping.pdf generated with shaping enabled!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
