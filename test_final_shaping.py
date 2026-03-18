from fpdf import FPDF
import os
import fitz

font_path = 'NotoSansDevanagari-Regular.ttf'
pdf = FPDF()
pdf.add_page()
pdf.add_font("Deva", fname=font_path)
pdf.set_font("Deva", size=20)
pdf.set_text_shaping(True)
pdf.text(50, 50, "प्रणाली")
pdf.output("test_final.pdf")

# Verify with fitz
doc = fitz.open("test_final.pdf")
page = doc[0]
text = page.get_text("text")
print(f"Extracted text: [{text.strip()}]")
# If it's shaped properly, sometimes get_text("text") returns the NFC form or the joined form.
# But more importantly, let's check the number of spans/chars
blocks = page.get_text("dict")["blocks"]
for b in blocks:
    for l in b["lines"]:
        for s in l["spans"]:
            print(f"Span text: [{s['text']}]")
