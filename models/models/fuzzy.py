import pandas as pd
from thefuzz import fuzz # pip install thefuzz

# 1. Load your data
df = pd.read_csv('fakti_bg.csv')
column_name = 'comment' # Change this to your actual column name

# 2. Find Exact Duplicates
exact_duplicates = df[df.duplicated(subset=[column_name], keep=False)]
print(f"Found {len(exact_duplicates)} exact duplicates.")

# 3. Find Near-Duplicates (Fuzzy Matching)
def find_near_matches(df, col, threshold=90):
    unique_comments = df[col].dropna().unique()
    results = []
    
    # Compare each comment against others
    for i in range(len(unique_comments)):
        for j in range(i + 1, len(unique_comments)):
            comment1 = unique_comments[i]
            comment2 = unique_comments[j]
            
            # Calculate similarity score (0-100)
            score = fuzz.token_sort_ratio(comment1, comment2)
            
            if score >= threshold:
                results.append({
                    'comment_a': comment1,
                    'comment_b': comment2,
                    'similarity': score
                })
    
    return pd.DataFrame(results)

# Run the fuzzy match
near_duplicates = find_near_matches(df, column_name, threshold=60)
print(near_duplicates)
