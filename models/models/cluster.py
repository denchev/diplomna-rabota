import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sentence_transformers import SentenceTransformer
import umap
import hdbscan

# 1. Зареждане на данните (Примерен вариант, замени с твоя DataFrame)
# Да приемем, че имаш DataFrame 'df' с колона 'comment_text'
data = {
    'comment_text': [
        "Тези избори през 2026 са абсолютно манипулирани! Всички са мафия!", # Потенциален трол
        "Гласувайте за номер 50! Само те ще спасят България! Купени избори!", # Потенциален бот
        "Гласувайте за номер 50! Само те ще спасят България! Купени избори!", # Copy-paste дубликат
        "Според мен избирателната активност в София ще бъде по-ниска от очакваното.", # Органичен
        "Някой знае ли къде мога да проверя секцията си за гласуване?", # Органичен
    ] * 50 # Изкуствено увеличаваме данните за примера
}

# Load data from fakt_bg.csv
data = pd.read_csv('fakti_bg.csv')
# Map comment column to 'comment_text' if necessary
if 'comment' in data.columns:
    data.rename(columns={'comment': 'comment_text'}, inplace=True)


df = pd.DataFrame(data)

# Важно: Премахваме САМО абсолютните текстови дубликати, за да не се чупи UMAP
df = df.drop_duplicates(subset=['comment_text']).reset_index(drop=True)
print(f"Брой уникални коментари за анализ: {len(df)}")


# ==========================================
# 2. КОМПОНЕНТ А: ИЗВЛИЧАНЕ НА СТИЛОМЕТРИЯ
# ==========================================
def extract_stylometric_features(text):
    char_count = len(text)
    word_count = len(text.split()) if char_count > 0 else 0
    
    if char_count == 0 or word_count == 0:
        return [0, 0, 0, 0, 0]
        
    # 1. Процент главни букви (крещене/Caps Lock)
    uppercase_ratio = sum(1 for c in text if c.isupper()) / char_count
    
    # 2. Брой удивителни знаци
    exclamation_count = text.count('!')
    
    # 3. Наличие на повтарящи се препинателни знаци (напр. "!!!", "??")
    multiple_punctuation = len(re.findall(r'[!?]{2,}', text))
    
    # 4. Средна дължина на думите
    avg_word_length = char_count / word_count
    
    # 5. Наличие на цифри (често срещано при ботове, въртящи номера на бюлетини)
    digit_count = sum(1 for c in text if c.isdigit()) / char_count

    return [word_count, uppercase_ratio, exclamation_count, multiple_punctuation, avg_word_length, digit_count]

print("\n[Етап 1] Извличане на стилометрични характеристики...")
raw_features = np.array([extract_stylometric_features(t) for t in df['comment_text']])

# Нормализация: Изключително важна стъпка, за да изравним тежестта на числата
scaler = MinMaxScaler()
stylometric_scaled = scaler.fit_transform(raw_features)


# ==========================================
# 3. КОМПОНЕНТ B: СЕМАНТИЧНИ EMBEDDINGS
# ==========================================
print("[Етап 2] Извличане на семантични вектори с Transformer модел...")
# Използваме лек, но изключително прецизен мултиезичен модел, който разбира отлично български език
transformer_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
semantic_embeddings = transformer_model.encode(df['comment_text'].tolist(), show_progress_bar=False)


# ==========================================
# 4. ХИБРИДНО СЛИВАНЕ (FEATURE FUSION)
# ==========================================
print("[Етап 3] Изграждане на хибридна матрица (Семантика + Стилометрия)...")
# Хоризонтално залепяме текстовия вектор и лингвистичния вектор за всеки коментар
hybrid_embeddings = np.hstack((semantic_embeddings, stylometric_scaled))
print(f"Размерност на хибридния вектор: {hybrid_embeddings.shape[1]} признака.")


# ==========================================
# 5. НАМАЛЯВАНЕ НА РАЗМЕРНОСТТА И КЛЪСТЕРИЗАЦИЯ
# ==========================================
print("[Етап 4] Намаляване на размерността с UMAP...")
# Динамично настройваме n_neighbors спрямо обема на данните, за да избегнем математически грешки
n_samples = len(df)
neighbors = min(15, max(2, n_samples - 1))

reducer = umap.UMAP(
    n_neighbors=neighbors,
    n_components=5,       # Намаляваме до 5 гъсти координати, идеални за HDBSCAN
    metric='cosine',      # Косинусово разстояние - най-доброто за текстови данни
    random_state=42
)
low_dim_embeddings = reducer.fit_transform(hybrid_embeddings)

print("[Етап 5] Провеждане на клъстеризация с HDBSCAN...")
clusterer = hdbscan.HDBSCAN(
    min_cluster_size=2,   # Минимален брой елементи за формиране на група
    min_samples=1,        # Настройка за по-ниска чувствителност към разпръснат шум
    metric='euclidean',
    cluster_selection_method='eom'
)
df['cluster'] = clusterer.fit_predict(low_dim_embeddings)


# ==========================================
# 6. АНАЛИЗ НА РЕЗУЛТАТИТЕ И СТАТИСТИКА
# ==========================================
print("\n==============================================")
print("             СТАТИСТИЧЕСКИ ДОКЛАД              ")
print("==============================================")
print(df['cluster'].value_counts().to_string())
print("Забележка: Стойност '-1' означава неидентифициран структурен шум (изолирани коментари).\n")

# Извеждане на профила на всеки открит клъстер
for cluster_id in sorted(df['cluster'].unique()):
    cluster_data = df[df['cluster'] == cluster_id]
    print(f"\n--- ПРОФИЛ НА КЛЪСТЕР {cluster_id} (Обем: {len(cluster_data)} коментара) ---")
    
    # Показваме първите 3 текста от клъстера
    print("Примерни текстове:")
    for i, txt in enumerate(cluster_data['comment_text'].head(3).values):
        print(f"  {i+1}. \"{txt}\"")


# ==========================================
# 7. ВИЗУАЛИЗАЦИЯ НА РЕЗУЛТАТИТЕ (За Глава 3)
# ==========================================
# Намаляваме до 2D пространство САМО с цел изчертаване на графика
visual_reducer = umap.UMAP(n_neighbors=neighbors, n_components=2, metric='cosine', random_state=42)
embeddings_2d = visual_reducer.fit_transform(hybrid_embeddings)

plt.figure(figsize=(10, 7))
scatter = plt.scatter(
    embeddings_2d[:, 0], 
    embeddings_2d[:, 1], 
    c=df['cluster'], 
    cmap='tab10', 
    s=40, 
    alpha=0.8, 
    edgecolors='black', 
    linewidths=0.5
)
plt.colorbar(scatter, label='Клъстер ID')
plt.title('Хибридна клъстеризация (Семантика + Стилометрия) на коментари "Избори 2026"')
plt.xlabel('UMAP Компонент 1')
plt.ylabel('UMAP Компонент 2')
plt.grid(True, linestyle='--', alpha=0.5)
plt.show()