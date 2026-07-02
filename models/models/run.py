from transformers import pipeline

# Use a multilingual model fine-tuned for text classification
# Note: You may need to look for a specific "MGT" (Machine Generated Text) fine-tuned version
detector = pipeline("text-classification", model="SaltSwell/multilingual-ai-detector")

# Bulgarian text example:
text = "Мразя да снимам тъпи концерти на слабо популярни групи!"

result = detector(text)
print(result)