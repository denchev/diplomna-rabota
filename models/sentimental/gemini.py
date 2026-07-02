import hashlib
import json
import pandas as pd
from pathlib import Path
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

CACHE_PATH = Path(__file__).resolve().parent / 'gemini_sentiment_cache.json'

client = genai.Client(api_key="")

class SentimentAnalysis(BaseModel):
    sentiment: str = Field(description="Трябва да бъде само един от следните низове: 'Позитивен', 'Негативен' или 'Неутрален'")
    confidence: float = Field(description="Число с плаваща запетая между 0.0 и 1.0, отразяващо твоята увереност")
    dominant_emotion: str = Field(description="Основната емоция на български език, напр. 'радост', 'разочарование', 'гняв', 'спокойствие'")


def load_cache():
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print(f"Warning: cache file {CACHE_PATH} is invalid. Rebuilding cache.")
    return {}


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


sentiment_cache = load_cache()

df = pd.read_csv('./input/svobodno_vreme/dnes_bg.csv')

def analyze_bulgarian_sentiment(text_content):
    cache_key = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
    if cache_key in sentiment_cache:
        return sentiment_cache[cache_key]

    prompt = f"""
    Ти си висококвалифициран лингвистичен анализатор. Анализирай емоционалния сентимент на следния текст на български език.
    
    Текст за анализ:
    "{text_content}"
    """

    try:
        # Извикване на Gemini API със структура за отговор (Structured Output)
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SentimentAnalysis,
            ),
        )
        
        # Тъй като използваме response_schema, response.text ГАРАНТИРАНО е валиден JSON според нашия модел
        data = json.loads(response.text)
        sentiment_cache[cache_key] = data
        save_cache(sentiment_cache)
        return data
        
    except Exception as e:
        print(f"Грешка при обработката на текста: {e}")
        return None

df = df.head(500)  # За тестови цели

# Store results in a dictionary
results = {}

for row in df.itertuples():
    text = row.comment
    article_url = row.article_url
    result = analyze_bulgarian_sentiment(text)
    if result:
        results[text] = result
        results[text]['article_url'] = article_url

        print(f"\nТекст: {text}")
        print(f"-> Сентимент: {result['sentiment']}")
        print(f"-> Увереност: {result['confidence']:.2%}")
        print(f"-> Доминираща емоция: {result['dominant_emotion']}")
        # print line number for tracking progress
        print(f"-> Обработен ред: {len(results)} от {len(df)}")

# Output results to a CSV file
output_df = pd.DataFrame.from_dict(results, orient='index')
output_df.to_csv('output/svobodno_vreme/dnes_bg_gemini.csv', encoding='utf-8-sig')
print("\nАнализът завърши! Резултатите са записани в 'output/svobodno_vreme/dnes_bg_gemini.csv'")

# Cost 2.78 USD -> 5.06 USD, 2,28 USD за 500 реда анализ на факти.бг