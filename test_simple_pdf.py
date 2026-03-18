from fpdf import FPDF
try:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.text(10, 10, "Hello World")
    pdf.output("hello.pdf")
    print("PDF OK")
except Exception as e:
    print(f"FAILED: {e}")
