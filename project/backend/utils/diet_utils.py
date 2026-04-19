import json

# Common allergy synonyms and category mappings
ALLERGY_SYNONYMS = {
    "groundnut": "peanuts",
    "groundnuts": "peanuts",
    "milk": "dairy",
    "cheese": "dairy",
    "yogurt": "dairy",
    "curd": "dairy",
    "paneer": "dairy",
    "butter": "dairy",
    "egg": "eggs",
    "shrimp": "seafood",
    "prawns": "seafood",
    "crab": "seafood",
    "lobster": "seafood",
    "wheat": "gluten",
    "barley": "gluten",
    "rye": "gluten",
}

def normalize_allergies(allergies_list):
    """
    Normalizes a list of allergies:
    1. Lowercase and trim
    2. Map synonyms (e.g., groundnut -> peanuts)
    3. Deduplicate 
    """
    if not allergies_list:
        return []
    
    if isinstance(allergies_list, str):
        try:
            # Handle if it was passed as a JSON string
            allergies_list = json.loads(allergies_list)
        except:
            # Handle comma separated if fallback
            allergies_list = [a.strip() for a in allergies_list.split(',')]

    normalized = set()
    for allergy in allergies_list:
        if not allergy:
            continue
        # Standardize
        item = str(allergy).strip().lower()
        
        # Map synonym
        canonical = ALLERGY_SYNONYMS.get(item, item)
        normalized.add(canonical)
        
    return sorted(list(normalized))
