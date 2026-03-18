import pdfplumber
with pdfplumber.open("sample.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"Page {i} chars: {len(page.chars)}")
        lines = page.extract_text_lines()
        print(f"Page {i} lines: {len(lines)}")
        for l in lines:
            print(f"LINE: {l['text']}")
