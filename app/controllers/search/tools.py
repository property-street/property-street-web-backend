import re
from difflib import SequenceMatcher

def normalize_query(query: str) -> dict:
    """
    Simple text preprocessor to:
    - Lowercase
    - Remove punctuation
    - Split words
    - Extract keywords, numbers, and location hints

    Args:
        query (str): string to normalize

    Returns:
        dict: mapping of original query, keywords and numbers.
    """
    q = query.lower().strip()
    tokens = re.findall(r'\b[\w]+\b', q)
    numbers = [int(t) for t in tokens if t.isdigit()]
    keywords = [t for t in tokens if not t.isdigit()]
    return {"original": query, "keywords": keywords, "numbers": numbers}


def text_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def rank_results(results, query):
    for r in results:
        text_fields = []
        data = r["data"]
        if hasattr(data, "title"): text_fields.append(data.title)
        if hasattr(data, "description"): text_fields.append(data.description)
        r["score"] = max([text_similarity(query, t) for t in text_fields if t], default=0)
    return sorted(results, key=lambda x: x["score"], reverse=True)
