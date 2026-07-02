from openai import OpenAI
import hashlib
import json
import pandas as pd
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / 'comment_sentiment_cache.json'

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

client = OpenAI(api_key="")
df = pd.read_csv('./input/izbori/dir_bg.csv')

def analyze_bulgarian_sentiment(text_content):
    cache_key = hashlib.sha256(text_content.encode('utf-8')).hexdigest()
    if cache_key in sentiment_cache:
        return sentiment_cache[cache_key]

    prompt = f"""
    Ти си висококвалифициран лингвистичен анализатор. Анализирай емоционалния сентимент на следния текст на български език.
    Върни резултата ОПРЕДЕЛЕНО и ЕДИНСТВЕНО като валиден JSON обект, без допълнителни обяснения, Markdown тагове или текст извън обекта.
    
    JSON обектът трябва да съдържа следните ключове:
    1. "sentiment" - (низ: "Позитивен", "Негативен" или "Неутрален")
    2. "confidence" - (число с плаваща запетая между 0.0 и 1.0, отразяващо твоята увереност)
    3. "dominant_emotion" - (низ на български: основната емоция, напр. "радост", "разочарование", "гняв", "спокойствие")

    Текст за анализ:
    "{text_content}"
    """

    response = client.chat.completions.create(
        model="gpt-5.5", # Или gpt-4o-mini / gpt-4o в зависимост от текущия ти достъп
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Извличане на текстовия отговор
    raw_output = response.choices[0].message.content.strip()
    
    # Парсване към Python речник
    try:
        data = json.loads(raw_output)
        sentiment_cache[cache_key] = data
        save_cache(sentiment_cache)
        return data
    except json.JSONDecodeError:
        print("Грешка при парсването на JSON. Суров отговор:", raw_output)
        return None

df = df.head(500)

# Store results in a dictionary
results = {}

# loop throu each csv line and get the comment and the article_url and analyze the sentiment of the comment
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
output_df.to_csv('output/izbori/dir_bg.csv', encoding='utf-8-sig')
print("\nАнализът завърши! Резултатите са записани в 'output/izbori/dir_bg.csv'")

# Cost 2.78 USD -> 5.06 USD, 2,28 USD за 500 реда анализ на факти.бг