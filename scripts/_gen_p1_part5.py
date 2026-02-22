"""Generate Prompt 1 attribute schemas and product synonym vocabulary."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_attribute_schemas() -> dict[str, dict[str, list[str]]]:
    return {
        "Food & Beverage": {
            "required": ["brand", "net_quantity", "fssai_license", "shelf_life", "nutritional_info"],
            "optional": ["ingredients", "allergens", "storage_instructions", "veg_nonveg", "organic_certification"],
        },
        "Grocery": {
            "required": ["brand", "net_quantity", "pack_type", "expiry_date", "country_of_origin"],
            "optional": ["ingredients", "batch_no", "mrp", "usage_instructions", "organic_certification"],
        },
        "Fashion": {
            "required": ["brand", "size", "color", "material", "wash_care"],
            "optional": ["pattern", "occasion", "fit_type", "sleeve_length", "neck_type"],
        },
        "Home & Kitchen": {
            "required": ["brand", "material", "dimensions", "weight", "care_instructions"],
            "optional": ["color", "capacity", "finish", "microwave_safe", "dishwasher_safe"],
        },
        "Electronics": {
            "required": ["brand", "model_number", "warranty", "power_requirement", "country_of_origin"],
            "optional": ["compatibility", "connector_type", "battery_included", "return_window", "installation_support"],
        },
        "Health & Wellness": {
            "required": ["brand", "net_quantity", "usage_instructions", "manufacturing_date", "expiry_date"],
            "optional": ["dosage", "ingredients", "storage_instructions", "certifications", "safety_warnings"],
        },
        "Beauty & Personal Care": {
            "required": ["brand", "net_quantity", "skin_or_hair_type", "expiry_date", "country_of_origin"],
            "optional": ["ingredients", "fragrance", "usage_instructions", "safety_warnings", "organic_certification"],
        },
        "Agriculture": {
            "required": ["brand", "net_quantity", "application_method", "crop_type", "composition"],
            "optional": ["dosage", "soil_suitability", "shelf_life", "safety_gear", "certification"],
        },
        "Handicrafts & Handloom": {
            "required": ["artisan_cluster", "material", "craft_type", "dimensions", "care_instructions"],
            "optional": ["weave_type", "region_of_origin", "color", "customization", "handmade_certification"],
        },
        "Stationery & Books": {
            "required": ["brand_or_author", "language", "format", "pages_or_quantity", "publisher_or_manufacturer"],
            "optional": ["isbn", "edition", "binding", "theme", "age_group"],
        },
    }


def build_product_synonyms() -> dict[str, dict[str, str]]:
    products = [
        "pickle", "saree", "spices", "turmeric", "chilli powder", "tea", "coffee", "rice", "wheat flour", "millet",
        "papad", "honey", "jaggery", "ghee", "lentils", "mustard oil", "soap", "shampoo", "hair oil", "face cream",
        "agarbatti", "dhoop", "diya", "candle", "kurta", "shirt", "t-shirt", "jeans", "lehenga", "dupatta",
        "blouse", "sandals", "sports shoes", "handbag", "wallet", "belt", "scarf", "stole", "bangle", "necklace",
        "earrings", "bedsheet", "curtain", "pillow cover", "carpet", "rug", "towel", "blanket", "utensils", "pressure cooker",
        "water bottle", "storage box", "planter", "wall art", "painting", "pottery", "lantern", "photo frame", "wooden chair", "table",
        "bookshelf", "mobile phone", "charger", "earphones", "power bank", "keyboard", "mouse", "usb drive", "led bulb", "fan",
        "mixer grinder", "iron", "water purifier", "yoga mat", "protein powder", "herbal tea", "essential oil", "sanitizer", "first aid kit", "thermometer",
        "face wash", "perfume", "deodorant", "nail polish", "foundation", "lipstick", "eyeliner", "hair serum", "vegetable seeds", "flower seeds",
        "fertilizer", "bio pesticide", "sprayer", "compost", "coir mat", "jute bag", "handloom saree", "khadi kurta", "notebook", "pen",
        "marker", "adhesive", "calculator", "children book", "exam guide", "sketchbook", "paint brush", "craft paper", "gift hamper", "souvenir",
        "brassware", "paper mache",
    ]
    synonyms = {
        p: {
            "en": p,
            "hi": p,
            "ta": p,
            "mr": p,
            "bn": p,
            "te": p,
            "kn": p,
            "gu": p,
        }
        for p in products
    }
    overrides = {
        "pickle": {"hi": "अचार", "ta": "ஊறுகாய்", "mr": "लोणचे", "bn": "আচার", "te": "ఊరగాయ", "kn": "ಉಪ್ಪಿನಕಾಯಿ", "gu": "અથાણું"},
        "saree": {"hi": "साड़ी", "ta": "சேலை", "mr": "साडी", "bn": "শাড়ি", "te": "చీర", "kn": "ಸೀರೆ", "gu": "સાડી"},
        "spices": {"hi": "मसाले", "ta": "மசாலா", "mr": "मसाले", "bn": "মশলা", "te": "మసాలా", "kn": "ಮಸಾಲೆ", "gu": "મસાલા"},
        "turmeric": {"hi": "हल्दी", "ta": "மஞ்சள்", "mr": "हळद", "bn": "হলুদ", "te": "పసుపు", "kn": "ಅರಿಶಿನ", "gu": "હળદર"},
        "tea": {"hi": "चाय", "ta": "தேநீர்", "mr": "चहा", "bn": "চা", "te": "టీ", "kn": "ಚಹಾ", "gu": "ચા"},
        "coffee": {"hi": "कॉफी", "ta": "காப்பி", "mr": "कॉफी", "bn": "কফি", "te": "కాఫీ", "kn": "ಕಾಫಿ", "gu": "કોફી"},
        "rice": {"hi": "चावल", "ta": "அரிசி", "mr": "तांदूळ", "bn": "চাল", "te": "బియ్యం", "kn": "ಅಕ್ಕಿ", "gu": "ચોખા"},
        "papad": {"hi": "पापड़", "ta": "அப்பளம்", "mr": "पापड", "bn": "পাপড়", "te": "పప్పడం", "kn": "ಹಪ್ಪಳ", "gu": "પાપડ"},
        "agarbatti": {"hi": "अगरबत्ती", "ta": "அகர்பத்தி", "mr": "अगरबत्ती", "bn": "আগরবাতি", "te": "అగరబత్తి", "kn": "ಅಗರಬತ್ತಿ", "gu": "અગરબત્તી"},
        "brassware": {"hi": "पीतल के बर्तन", "ta": "பித்தளை பொருட்கள்", "mr": "पितळी भांडी", "bn": "পিতলের জিনিস", "te": "పిత్తల వస్తువులు", "kn": "ಪಿತ್ತಳ ವಸ್ತುಗಳು", "gu": "પીતળ વાસણ"},
    }
    for key, mapping in overrides.items():
        if key in synonyms:
            synonyms[key].update(mapping)
    return synonyms


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "data"
    write_json(root / "catalog_templates" / "attribute_schemas.json", build_attribute_schemas())
    write_json(root / "vocabulary" / "product_synonyms.json", build_product_synonyms())
    print("generated attribute_schemas and product_synonyms")


if __name__ == "__main__":
    main()
