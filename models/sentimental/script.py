import pandas as pd
from openai import OpenAI
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. ИНИЦИАЛИЗАЦИЯ НА КЛИЕНТА
BGGPT_API_KEY = ""
MAX_WORKERS = 15  # Брой паралелни нишки. Можеш да го вдигнеш до 20-30, ако API-то позволява.

client = OpenAI(
    base_url="https://api.bggpt.ai/v1",
    api_key=BGGPT_API_KEY
)

# 2. ЗАРЕЖДАНЕ НА ДАННИТЕ
df = pd.read_csv('./sentimental/dnes_bg.csv')

# Примерни демо данни

#df = pd.DataFrame(demo_data)
# get only the first 100 rows for testing
df = df.head(100)


# Създаваме празна колона за резултатите
df['sentiment'] = "Neutral"

# 3. ФУНКЦИЯ ЗА ОБРАБОТКА НА ЕДИНИЧЕН КОМЕНТАР
def analyze_single_comment(index, text):
    if pd.isna(text) or not isinstance(text, str):
        return index, "Neutral"
        
    try:
        response = client.chat.completions.create(
            model="bggpt-gemma-3-27b-fp8",
            messages=[
                {
                    "role": "system", 
                    "content": """Ти си обективен експерт по лингвистичен анализ. Твоята задача е да определиш сентимента на подадения български коментар. 
                    Следвай стриктно тези правила:
                    1. Маркирай като 'Negative' САМО коментари, които съдържат явен гняв, обидни думи, остра критика, агресия или силно разочарование.
                    2. Ако коментарът просто съобщава факти, задава въпроси или изразява мнение без агресивни думи, го маркирай като 'Neutral'.
                    3. Отговори САМО с една от следните три думи: Positive, Neutral или Negative. Не пиши нищо друго."""
                },
                {
                    "role": "user", 
                    "content": f"Анализирай този коментар: {text}"
                }
            ],
            temperature=0.1,
            max_tokens=5
        )
        
        result = response.choices[0].message.content.strip()
        
        # Напасване на изхода
        if result not in ["Positive", "Neutral", "Negative"]:
            if "Positive" in result or "позитивен" in result.lower(): result = "Positive"
            elif "Negative" in result or "негативен" in result.lower(): result = "Negative"
            else: result = "Neutral"
            
        return index, result
        
    except Exception as e:
        return index, "Neutral"

# 4. СЛУЖЕБЕН СЛОЙ ЗА ПАРАЛЕЛИЗАЦИЯ (ThreadPoolExecutor)
print(f"Стартиране на високоскоростен паралелен анализ с {MAX_WORKERS} нишки...")

results = {}
# Използваме ThreadPoolExecutor за менажиране на нишките
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    # Подаваме всички задачи на нишките
    futures = {
        executor.submit(analyze_single_comment, idx, row['comment']): idx 
        for idx, row in df.iterrows()
    }
    
    # Визуализираме прогреса в реално време, докато нишките завършват
    for future in tqdm(as_completed(futures), total=len(futures)):
        idx, sentiment_result = future.result()
        results[idx] = sentiment_result

# 5. НАПАСВАНЕ НА РЕЗУЛТАТИТЕ СПРЯМО ОРИГИНАЛНИЯ ИНДЕКС И ЗАПИС
for idx, sentiment in results.items():
    df.at[idx, 'sentiment'] = sentiment

output_file = "dnes_bg_gpt_analyzed_comments.csv"
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\nВисокоскоростният анализ завърши! Резултатите са в: '{output_file}'")