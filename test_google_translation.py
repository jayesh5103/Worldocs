from deep_translator import GoogleTranslator
text = "W o r l d d o c -  c l o u d  b a s e d"
translated = GoogleTranslator(source="auto", target="mr").translate(text)
print("Translating spaced English:", repr(translated))
