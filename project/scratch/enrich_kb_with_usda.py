import json
import os
import re

# Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USDA_FILE = os.path.join(ROOT_DIR, "FoodData_Central_foundation_food_json_2025-12-18.json")
KB_FILE = os.path.join(ROOT_DIR, "backend", "data", "dietary_knowledge.json")

# Clinical templates for benefits
BENEFIT_TEMPLATES = {
    "vitamin_c": "Potent antioxidant density supports vascular integrity and immune resilience.",
    "iron": "Supports oxygen transport and hematopoietic synthesis for energy metabolism.",
    "fiber": "Enhances glycemic stability and promotes digestive microbiome integrity.",
    "protein": "Provides essential amino acid substrates for tissue repair and metabolic balance.",
    "calcium": "Critical for skeletal density and neuromuscular signalling integrity.",
    "potassium": "Supports cardiovascular rhythm and optimal electrolyte homeostasis.",
    "magnesium": "Cofactor for 300+ enzymatic reactions, supporting neuronal and muscular health.",
    "vitamin_a": "Vital for retinal health and mucosal immune barrier function.",
    "vitamin_b12": "Essential for neurological myelin maintenance and DNA synthesis.",
    "carotenoids": "Powerful phytonutrients for cellular protection and retinal health."
}

# Mapping USDA nutrient names to our standard tags
NUTRIENT_MAPPING = {
    "Vitamin C, total ascorbic acid": "vitamin_c",
    "Iron, Fe": "iron",
    "Fiber, total dietary": "fiber",
    "Protein": "protein",
    "Calcium, Ca": "calcium",
    "Potassium, K": "potassium",
    "Magnesium, Mg": "magnesium",
    "Vitamin A, RAE": "vitamin_a",
    "Vitamin B-12": "vitamin_b12",
    "Carotene, beta": "carotenoids",
    "Lutein + zeaxanthin": "carotenoids"
}

def clean_name(name):
    # e.g. "Hummus, commercial" -> "Hummus"
    # "Nuts, almonds, dry roasted..." -> "Almonds"
    name = name.split(",")[0].strip()
    # Remove some common prefix patterns if they exist
    name = re.sub(r"^(Nuts|Oil|Flour|Beans|Seeds|Fish|Egg|Cheese|Milk), ", "", name, flags=re.I)
    return name.lower()

def enrich():
    print(f"Loading USDA data from {USDA_FILE}...")
    with open(USDA_FILE, "r") as f:
        usda_data = json.load(f)
        
    print(f"Loading Knowledge Base from {KB_FILE}...")
    with open(KB_FILE, "r") as f:
        kb_data = json.load(f)

    new_entries_count = 0
    
    for food_entry in usda_data.get("FoundationFoods", []):
        raw_name = food_entry["description"]
        name = clean_name(raw_name)
        
        # Don't overwrite hand-curated ones if they are already "perfect"
        if name in kb_data["food_details"]:
            continue
            
        nutrients = food_entry.get("foodNutrients", [])
        found_tags = []
        best_nutrient = None
        max_val = 0
        
        for n in nutrients:
            n_name = n.get("nutrient", {}).get("name")
            amount = n.get("amount", 0)
            
            if n_name in NUTRIENT_MAPPING:
                tag = NUTRIENT_MAPPING[n_name]
                found_tags.append(tag)
                
                # Simple weight for "strength" - mg vs g
                unit = n.get("nutrient", {}).get("unitName", "")
                val = amount * 1000 if unit == "g" else amount
                if val > max_val:
                    max_val = val
                    best_nutrient = tag
                    
        if not best_nutrient:
            continue # Skip foods without our target nutrients
            
        # Determine category tags based on USDA foodCategory
        cat = food_entry.get("foodCategory", {}).get("description", "").lower()
        cat_tags = []
        if any(x in cat for x in ["vegetable", "legume", "fruit"]):
            cat_tags += ["meal_lunch", "meal_dinner"]
        if any(x in cat for x in ["dairy", "egg", "cereal", "grain"]):
            cat_tags += ["meal_breakfast"]
        if any(x in cat for x in ["nut", "seed", "fruit"]):
            cat_tags += ["meal_snack"]

        # Final structure
        kb_data["food_details"][name] = {
            "tags": list(set(found_tags + cat_tags)),
            "benefits": BENEFIT_TEMPLATES.get(best_nutrient, "Rich in essential clinical-grade nutrients.")
        }
        new_entries_count += 1

    print(f"Enriched KB with {new_entries_count} new USDA foods.")
    
    with open(KB_FILE, "w") as f:
        json.dump(kb_data, f, indent=2)
    print("KB successfully updated.")

if __name__ == "__main__":
    enrich()
