from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
import pandas as pd

# 1. Your texts (If N is very small, we must adjust parameters)
df = pd.read_csv('fakti_bg.csv')
column_data = df['comment'].head(500)
data_array = column_data.tolist()
docs = data_array

# 2. Adjust UMAP for small datasets
# n_neighbors: How many neighbors to look at (must be < number of docs)
# n_components: Dimensions to reduce to (keep it low for small data)
umap_model = UMAP(n_neighbors=3, n_components=2, min_dist=0.0, metric='cosine')

# 3. Adjust HDBSCAN
# min_cluster_size: Minimum number of items to form a topic
hdbscan_model = HDBSCAN(min_cluster_size=2, metric='euclidean', prediction_data=True)

# 4. Use a Multilingual Embedding model
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 5. Initialize BERTopic with these sub-models
topic_model = BERTopic(
    embedding_model=embedding_model,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    language="multilingual"
)

topics, probs = topic_model.fit_transform(docs)

topic_info = topic_model.get_topic_info()

results_df = pd.DataFrame({
    "Document_Text": docs,
    "Topic_ID": topics
})

# 3. Обединяване с имената на темите и ключовите думи
results_df = results_df.merge(topic_info[['Topic', 'Name', 'Representation']], 
                              left_on='Topic_ID', 
                              right_on='Topic')

# 4. Премахване на дублиращата се колона и преименуване
results_df = results_df.drop(columns=['Topic'])
results_df.rename(columns={'Name': 'Topic_Name', 'Representation': 'Keywords'}, inplace=True)

# 5. Записване в CSV (важно е encoding='utf-8-sig' за кирилицата в Excel)
results_df.to_csv("clustering_results.csv", index=False, encoding='utf-8-sig')

print("Резултатите са записани успешно в clustering_results.csv")