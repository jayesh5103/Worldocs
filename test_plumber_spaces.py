import pdfplumber

with pdfplumber.open("sample.pdf") as pdf:
    for page in pdf.pages:
        char_buckets = {}
        for ch in page.chars:
            key = round(ch["top"] / 4) * 4
            char_buckets.setdefault(key, []).append(ch)

        for key in sorted(char_buckets):
            chs = sorted(char_buckets[key], key=lambda c: c["x0"])
            line_text = "".join(c["text"] for c in chs)
            print(f"[{line_text}]")
