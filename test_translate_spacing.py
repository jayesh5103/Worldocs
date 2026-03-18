from deep_translator import GoogleTranslator

text1 = "Worlddocs - cloud based document translation"
print("Standard text:", repr(GoogleTranslator(source="en", target="mr").translate(text1)))

text2 = "W o r l d d o c s - c l o u d b a s e d"
print("Spaced text:", repr(GoogleTranslator(source="en", target="mr").translate(text2)))
