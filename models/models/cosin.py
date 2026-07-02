import pandas as pd
import nltk
from nltk.corpus import stopwords
from snowballstemmer import stemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Download Bulgarian stop words
nltk.download('stopwords')
bulgarian_stopwords = stopwords.words('bulgarian')
bul_stemmer = stemmer('bulgarian')

# Function to preprocess Bulgarian text
def preprocess_bulgarian(text):
    # Lowercase and split
    words = str(text).lower().split()
    # Stem words and remove stop words
    stemmed = [bul_stemmer.stemWord(w) for w in words if w not in bulgarian_stopwords]
    return " ".join(stemmed)

# 1. Load Data
df = pd.read_csv('fakti_bg.csv')
target_col = 'comment'

# 2. Apply Preprocessing
# This turns "кучетата тичат" into "кучет тич" (roots)
df['processed_text'] = df[target_col].apply(preprocess_bulgarian)

# 3. Vectorize using the processed column
vectorizer = TfidfVectorizer() 
tfidf_matrix = vectorizer.fit_transform(df['processed_text'])

# 4. Compute Similarity
sim_matrix = cosine_similarity(tfidf_matrix)

# 5. Extract results (0.5 to 1.0)
pairs = []
for i in range(len(sim_matrix)):
    for j in range(i + 1, len(sim_matrix)):
        score = sim_matrix[i, j]
        if 0.5 <= score < 1.0:
            pairs.append({
                'Item_1': df[target_col].iloc[i],
                'Item_2': df[target_col].iloc[j],
                'Score': round(score, 4)
            })

results_df = pd.DataFrame(pairs)
print(results_df.head(10))