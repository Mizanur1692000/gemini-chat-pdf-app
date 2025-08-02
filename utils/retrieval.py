import pandas as pd

def retrieve_relevant_pages(csv_path: str, query: str, top_k: int = 3):
    """
    Naive retrieval: rank by term frequency of query in each page's text.
    Returns concatenated context string.
    """
    df = pd.read_csv(csv_path)
    df["score"] = df["text"].str.lower().apply(lambda t: t.count(query.lower()) if isinstance(t, str) else 0)
    top = df.sort_values("score", ascending=False).head(top_k)
    context = "\n\n".join(
        f"Page {row['page']}:\n{row['text']}" for _, row in top.iterrows() if row["score"] > 0
    )
    return context
