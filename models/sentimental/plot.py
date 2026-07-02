import pandas as pd
import matplotlib.pyplot as plt

# 1. Setup Cyrillic font support & sizing
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11

# 2. Load the dataset
df = pd.read_csv('output/izbori/dnes_bg_with_news_data_gemini.csv')

# 3. Aggregate data: Count total comments and count unique clusters per article emotion
scatter_data = df.groupby('article_dominant_emotion').agg(
    total_comments=('comment_dominant_emotion', 'count'),
    unique_clusters=('comment_dominant_emotion', 'nunique')
).reset_index()

# 4. Initialize the plot layout
fig, ax = plt.subplots(figsize=(12, 8))

# 5. Separate 'разочарование' from other emotions for custom styling

# Plot general data points
ax.scatter(
    other_rows['total_comments'], 
    other_rows['unique_clusters'], 
    color='#34495e', 
    s=150, 
    edgecolor='black', 
    alpha=0.8, 
    label='Други емоции (Other Emotions)'
)


# 6. Annotate the points on the grid dynamically
for _, row in scatter_data.iterrows():
    if row['article_dominant_emotion'] == 'разочарование':
        ax.text(
            row['total_comments'] + 2, 
            row['unique_clusters'], 
            f"{row['article_dominant_emotion']} ({row['unique_clusters']} клъстера)", 
            color='#c0392b', 
            weight='bold',
            va='center'
        )
    elif row['total_comments'] > 5 or row['unique_clusters'] > 5:
        # Avoid clutter by only labeling emotions with substantial data points
        ax.text(
            row['total_comments'] + 2, 
            row['unique_clusters'], 
            row['article_dominant_emotion'], 
            color='#555555',
            alpha=0.9,
            va='center',
            fontsize=9
        )

# 7. Labels, grids, and legend customization
ax.set_title('Връзка между общия брой коментари и уникалните емоционални клъстери', fontsize=14, fontweight='bold', pad=15)
ax.set_xlabel('Общ брой коментари за емоция на статията (Total Comments)', fontsize=12)
ax.set_ylabel('Брой уникални емоционални клъстери в коментарите (Unique Clusters)', fontsize=12)
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(loc='lower right')

# 8. Save the final chart
plt.tight_layout()
plt.savefig('pure_matplotlib_scatter.png', dpi=150)