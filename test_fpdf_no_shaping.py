from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()
font_path = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
pdf.add_font("Deva", fname=font_path)

# Deliberately NOT calling set_text_shaping(True)
pdf.set_font("Deva", size=20)
text = "वर्ल्डडॉक - क्लाउड बेस्ड डॉक्युमेंट ट्रान्सलेशन प्रणाली"
pdf.text(x=50, y=100, text=text)

pdf.output("test_no_shaping.pdf")
print("SUCCESS: test_no_shaping.pdf generated")
