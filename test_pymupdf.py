import fitz
import sys
import os

try:
    doc = fitz.open()
    page = doc.new_page()
    fontfile = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
    
    # insert_font returns the internal name if not provided, but we can provide a simple one
    page.insert_font(fontname="F0", fontfile=fontfile)
    print("PyMuPDF features:", fitz.TOOLS.mupdf_version())
    print("Inserting text...")
    
    # insert_text with internal fontname
    page.insert_text((100, 100), "हिन्दी और मराठी अनुवाद", fontname="F0", fontsize=20)
    
    # Also test text box with HTML (requires simple string for font-family, we will just use the loaded font)
    doc.save("test_fitz.pdf")
    print("Saved test_fitz.pdf successfully!")
except Exception as e:
    print(f"Error occurred: {e}", file=sys.stderr)
