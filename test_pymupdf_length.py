import fitz
import os
fontfile = 'NotoSansDevanagari-Regular.ttf' if os.path.exists('NotoSansDevanagari-Regular.ttf') else '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'
doc = fitz.open()
page = doc.new_page()
font = fitz.Font(fontfile=fontfile)
text = "हिन्दी और मराठी अनुवाद"
# Need to measure length
length = font.text_length(text, fontsize=20)
print("Length:", length)
