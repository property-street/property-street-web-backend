# from nltk.stem import PorterStemmer

# stemmer = PorterStemmer()

def create_search_segments(search_string, stopwords, categories):
    """
    Process the search string to extract individual words and phrases,
    tagging them with categories if matched.
    """
    # Step 1: Tokenize and initialize variables
    tokens = search_string.split()
    segment_indices = [0]
    results = []
    
    # Identify segments using stopwords
    for i, token in enumerate(tokens):
        if token in stopwords:
            if segment_indices[-1] != i:
                segment = tokens[segment_indices[-1]:i]
                results.extend(process_segment(segment, categories))
            segment_indices.append(i + 1)
    
    # Process the final segment
    if segment_indices[-1] < len(tokens):
        segment = tokens[segment_indices[-1]:]
        results.extend(process_segment(segment, categories))
    
    return results


def process_segment(segment, categories):
    """
    Process a single segment by extracting words and phrases,
    and tagging them with categories.
    """
    results = []
    n = len(segment)
    
    # Use a sliding window for all word combinations
    for start in range(n):
        phrase = []
        for end in range(start, n):
            phrase.append(segment[end])
            combined_phrase = " ".join(phrase)

            # Apply stemming
            # stemmed_phrase = " ".join([stemmer.stem(word) for word in phrase])
            
            # Match category
            category = tag_search_token(combined_phrase, categories)
            results.append((combined_phrase, category))
    
    return results


def tag_search_token(phrase, categories):
    """
    Match a phrase against categories and return the tag.
    """
    phrase_lower = phrase.lower()
    for key, tag in categories.items():
        if key in phrase_lower:
            return tag
    return "none"