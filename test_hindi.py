from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

font_path = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
try:
    pdfmetrics.registerFont(TTFont('Devanagari', font_path))
except Exception as e:
    print(f"Font error: {e}")

c = canvas.Canvas("test_hindi.pdf")
try:
    c.setFont("Devanagari", 20)
    text = "हिन्दी और मराठी अनुवाद" # Hindi and Marathi translation
    c.drawString(100, 700, text)
    c.save()
    print("Saved test_hindi.pdf")
except Exception as e:
    print(f"Error: {e}")
