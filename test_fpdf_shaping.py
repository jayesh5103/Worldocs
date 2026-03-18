from fpdf import FPDF
import os

pdf = FPDF()
pdf.add_page()
font_path = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'

pdf.add_font("Deva", fname=font_path)
pdf.set_font("Deva", size=20)

text = "क्लाउड तंत्रज्ञान"

try:
    print("Does pdf.set_text_shaping exist?", hasattr(pdf, 'set_text_shaping'))
    # In recent versions of fpdf2, text shaping is activated globally or per font
    print("FPDF VERSION:", getattr(FPDF, '__version__', 'unknown'))
    
    # Let's inspect signature
    import inspect
    sig = inspect.signature(pdf.add_font)
    print("add_font params:", sig.parameters.keys())
except Exception as e:
    print(e)

pdf.output("test_shaping.pdf")
print("Saved test_shaping.pdf")
