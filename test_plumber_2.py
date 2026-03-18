import pdfplumber
with pdfplumber.open("sample.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i} ---")
        print(f"Raw text: [{page.extract_text()}]")
        lines = page.extract_text_lines()
        print(f"Lines count: {len(lines)}")
        for line in lines:
            print(f"Line text: [{line['text']}]")
