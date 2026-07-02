import hashlib
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

client = genai.Client(api_key="")

CACHE_PATH = Path(__file__).resolve().parent / 'article_sentiment_gemini_cache.json'

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

df = pd.read_csv('./output/svobodno_vreme/dnes_bg.csv')

def extract_json_from_text(raw_output):
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw_output, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None


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

    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SentimentAnalysis,
        ),
    )
    
    # Извличане на текстовия отговор
    data = json.loads(response.text)
    print(data)
    sentiment_cache[cache_key] = data
    save_cache(sentiment_cache)
    return data

# Read only the unique "article_url" values from the CSV file
unique_urls = df['article_url'].unique()

# Reduce to only 10
#unique_urls = unique_urls[:2]

# Get the content of the website for each unique URL and store it in a dictionary
url_content = {}
for url in unique_urls:
    # Here you would implement the logic to fetch the content of the website for the given URL
    # For example, you could use requests and BeautifulSoup to scrape the content
    # Timeout for the request should be no more than 2 seconds
    response = requests.get(url, timeout=2)
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.get_text()
    
    print(f"Fetched content for URL: {url}")
    article_content = soup.select_one('.article-content') # fakti.bg: .news-text, dnes.bg: .article-content, mediapool.bg: .c-text.c-article-content, dir.bg: .article-content .article-body
    article_title = soup.select_one('.article-header h1') # fakti.bg: .news-title, dnes.bg: .article-header h1, mediapool.bg: .c-heading.c-heading_size_1.c-heading_spaced, dir.bg: .article-main-section h1.title
    title_text = article_title.get_text(strip=True) if article_title else None
    if article_content:
        article_text = article_content.get_text()
        #print(f"Article content for URL: {url}:\n{article_text}\n")
        url_content[url] = {'content': article_text, 'title': title_text}
    else:
        print(f"No article content found for URL: {url}\n")
        url_content[url] = {'content': content, 'title': title_text}


# For item in the url_content dictionary, run the gpt model to analyze the sentiment of the content and store the result in a new dictionary
sentiment_results = {}
for url, data in url_content.items():
    sentiment = analyze_bulgarian_sentiment(data['content'])
    title_sentiment = analyze_bulgarian_sentiment(data['title'])
    if sentiment is None:
        sentiment = {'sentiment': None, 'confidence': None, 'dominant_emotion': None}
    sentiment_results[url] = {
        **sentiment,
        'article_title': data.get('title'),
        'article_title_sentiment': title_sentiment.get('sentiment'),
        'article_title_confidence': title_sentiment.get('confidence'),
        'article_title_dominant_emotion': title_sentiment.get('dominant_emotion'),
    }
    print(f"Sentiment analysis for URL: {url}:\n{sentiment_results[url]}\n")

print(sentiment_results)

# Get each line of the input CSV and add the newly found sentiment results
final_result = {}
for index, row in df.iterrows():
    article_url = row['article_url']
    comment = row['comment']
    article_sentiment = sentiment_results.get(article_url, {'sentiment': None, 'confidence': None, 'dominant_emotion': None, 'article_title': None})
    #print(article_sentiment)
    final_result[comment] = {
        'article_url': article_url,
        'article_title': article_sentiment.get('article_title'),
        'comment_sentiment': row.sentiment,
        'comment_confidence': row.confidence,
        'comment_dominant_emotion': row.dominant_emotion,
        'article_title_sentiment': article_sentiment.get('article_title_sentiment'),
        'article_title_confidence': article_sentiment.get('article_title_confidence'),
        'article_title_dominant_emotion': article_sentiment.get('article_title_dominant_emotion'),
        'article_sentiment': article_sentiment.get('sentiment'),
        'article_confidence': article_sentiment.get('confidence'),
        'article_dominant_emotion': article_sentiment.get('dominant_emotion'),
    }

# Create an ouput CSV file with the URL to the article and the sentiment analysis result
output_df = pd.DataFrame.from_dict(final_result, orient='index')

output_df.to_csv('output/svobodno_vreme/dnes_bg_with_news_data_gemini.csv', encoding='utf-8-sig', index_label='comment_text') 