import pdfplumber
with pdfplumber.open("sample.pdf") as pdf:
    for page in pdf.pages:
        lines = page.extract_text_lines()
        for i, line in enumerate(lines):
            print(f"Line {i}: [{line['text']}] at x0={line['x0']}, bottom={line['bottom']}")
