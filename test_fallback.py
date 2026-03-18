from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()

fallback = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
primary = 'NotoSans-Regular.ttf' if os.path.exists('NotoSans-Regular.ttf') else '/Library/Fonts/Arial Unicode.ttf'

pdf.add_font("Primary", fname=primary)
pdf.add_font("Deva", fname=fallback)

# Setup fallback list
pdf.set_fallback_fonts(["Deva"])
pdf.set_font("Primary", size=15)

text = "This is English mixed with हिन्दी आणि मराठी अनुवाद!"

pdf.text(x=20, y=50, text=text)

pdf.output("test_fallback.pdf")
print("SUCCESS: test_fallback.pdf generated with fallback fonts!")
