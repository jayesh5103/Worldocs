import pdfplumber
import os

# Create a small PDF with spaces to test
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font("helvetica", size=12)
pdf.text(10, 10, "This is a test with spaces")
pdf.output("space_test.pdf")

with pdfplumber.open("space_test.pdf") as pdf:
    for page in pdf.pages:
        lines = page.extract_text_lines()
        for line in lines:
            print(f"Line: [{line['text']}]")
