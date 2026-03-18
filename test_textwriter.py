import fitz
import os

doc = fitz.open()
page = doc.new_page()
fontfile = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
font = fitz.Font(fontfile=fontfile)

try:
    tw = fitz.TextWriter(page.rect)
    # textwriter may have a language parameter or shaping
    # Let's try appending text
    tw.append((50, 50), "हिन्दी और मराठी अनुवाद", font=font, fontsize=20)
    tw.write_text(page)
    doc.save("test_tw.pdf")
    print("Saved test_tw.pdf")
except Exception as e:
    print(f"Error: {e}")
