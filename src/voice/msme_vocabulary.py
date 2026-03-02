"""Multilingual MSME vocabulary normalization utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
MSME_TERMS_PATH = ROOT_DIR / "data" / "vocabulary" / "msme_terms.json"
PRODUCT_SYNONYMS_PATH = ROOT_DIR / "data" / "vocabulary" / "product_synonyms.json"

_LOADED_EXTERNAL_SYNONYMS: dict[str, list[str]] | None = None


def _merge_entry(target: dict[str, list[str]], canonical: str, variants: list[str]) -> None:
    key = str(canonical or "").strip().lower()
    if not key:
        return
    bucket = target.setdefault(key, [])
    for raw in variants:
        value = str(raw or "").strip().lower()
        if value and value not in bucket:
            bucket.append(value)


def _build_default_synonyms() -> dict[str, list[str]]:
    synonyms: dict[str, list[str]] = {}

    product_terms = {
        "mango pickle": ["aam ka achaar", "aam ka achar", "aam achaar", "आम का अचार", "mango achar"],
        "lemon pickle": ["nimbu achar", "नींबू अचार", "lemon achar"],
        "mixed pickle": ["mix achar", "मिक्स अचार"],
        "turmeric": ["haldi", "हल्दी", "manjal", "pasupu"],
        "red chilli powder": ["lal mirch powder", "लाल मिर्च पाउडर", "molaga podi"],
        "coriander powder": ["dhaniya powder", "धनिया पाउडर"],
        "cumin powder": ["jeera powder", "जीरा पाउडर"],
        "garam masala": ["गरम मसाला", "hot spice mix"],
        "tea": ["chai", "चाय", "cha"],
        "coffee": ["filter coffee", "कॉफी", "kapi"],
        "saree": ["sari", "साड़ी", "saadi", "pudava"],
        "handloom saree": ["karigar saree", "हैंडलूम साड़ी"],
        "silk saree": ["resham saree", "रेशम साड़ी", "pattu saree"],
        "cotton bedsheet": ["sooti chadar", "सूती चादर", "cotton chadar"],
        "dupatta": ["दुपट्टा", "stole cloth"],
        "kurta": ["kurti", "कुर्ती", "kurti"],
        "lehenga": ["घाघरा", "ghagra"],
        "blouse": ["चोली", "choli"],
        "leather bag": ["chamde ka bag", "चमड़े का बैग", "leather purse"],
        "jute bag": ["jute ka thela", "joot bag", "जूट बैग"],
        "wallet": ["batua", "बटुआ"],
        "belt": ["kamar belt", "कमर बेल्ट"],
        "brass utensil": ["peetal ka bartan", "पीतल का बर्तन", "pital bartan"],
        "steel utensil": ["steel bartan", "स्टील बर्तन"],
        "copper bottle": ["tambe ki bottle", "तांबे की बोतल"],
        "pressure cooker": ["प्रेशर कुकर", "cooker"],
        "tawa": ["flat pan", "तवा"],
        "kadhai": ["कड़ाही", "karahi"],
        "storage container": ["dabba", "डिब्बा", "container box"],
        "handmade soap": ["haath ka sabun", "हाथ का साबुन"],
        "face wash": ["muh dhone ka gel", "फेस वॉश"],
        "shampoo": ["बाल धोने का शैम्पू", "hair shampoo"],
        "hair oil": ["tel", "तेल", "kesh tel"],
        "face cream": ["mukh cream", "चेहरा क्रीम"],
        "lipstick": ["lip stick", "लिपस्टिक"],
        "eyeliner": ["काजल लाइनर", "eye liner"],
        "perfume": ["itr", "इत्र", "attar"],
        "deodorant": ["deo", "डियो"],
        "incense sticks": ["agarbatti", "अगरबत्ती", "dhoop"],
        "camphor": ["kapoor", "कपूर"],
        "cotton wick": ["batti", "रुई बत्ती"],
        "diya": ["दीया", "lamp diya"],
        "candle": ["मोमबत्ती", "mombatti"],
        "led bulb": ["एलईडी बल्ब", "bulb led"],
        "mobile charger": ["charger", "मोबाइल चार्जर"],
        "earphones": ["ear phone", "इयरफोन"],
        "power bank": ["पावर बैंक", "battery bank"],
        "usb drive": ["pen drive", "पेन ड्राइव"],
        "laptop": ["notebook computer", "लैपटॉप"],
        "keyboard": ["कीबोर्ड", "key board"],
        "mouse": ["माउस", "mouse device"],
        "water purifier": ["RO purifier", "पानी शुद्धिकरण"],
        "mixer grinder": ["मिक्सर ग्राइंडर", "mixie"],
        "electric iron": ["press", "इलेक्ट्रिक प्रेस"],
        "fan": ["ceiling fan", "पंखा"],
        "furniture": ["furnishing item", "फर्नीचर"],
        "wooden chair": ["लकड़ी की कुर्सी", "wood chair"],
        "table": ["टेबल", "desk"],
        "bookshelf": ["book shelf", "बुकशेल्फ"],
        "wall art": ["दीवार सजावट", "wall decor"],
        "painting": ["चित्र", "art painting"],
        "photo frame": ["फोटो फ्रेम", "frame"],
        "pottery": ["मिट्टी बर्तन", "ceramic pottery"],
        "lantern": ["लालटेन", "lamp lantern"],
        "carpet": ["कालीन", "kaleen"],
        "rug": ["दरी", "floor rug"],
        "curtain": ["पर्दा", "parda"],
        "pillow cover": ["तकिया कवर", "cushion cover"],
        "blanket": ["कंबल", "kambal"],
        "towel": ["तौलिया", "gamcha"],
        "notebook": ["copy", "कॉपी", "notepad"],
        "pen": ["कलम", "ball pen"],
        "pencil": ["पेन्सिल", "pencil stick"],
        "marker": ["sketch pen", "मार्कर"],
        "adhesive": ["glue", "गोंद"],
        "craft paper": ["रंगीन कागज", "art paper"],
        "children book": ["bachchon ki kitab", "बच्चों की किताब"],
        "exam guide": ["guide book", "तैयारी गाइड"],
        "vegetable seeds": ["sabzi beej", "सब्जी बीज"],
        "flower seeds": ["phool beej", "फूल बीज"],
        "fertilizer": ["khad", "खाद"],
        "organic fertilizer": ["jaivik khad", "जैविक खाद"],
        "bio pesticide": ["jeevanu nashak", "बायो पेस्टिसाइड"],
        "sprayer": ["spray pump", "स्प्रेयर"],
        "compost": ["compost khad", "कम्पोस्ट"],
        "cocopeat": ["coco peat", "कोकोपीट"],
        "mulch film": ["mulching sheet", "मल्च फिल्म"],
        "shade net": ["green net", "शेड नेट"],
        "animal feed": ["pashu aahar", "पशु आहार"],
        "papad": ["pappad", "पापड़"],
        "namkeen": ["savory snacks", "नमकीन"],
        "cookies": ["biscuits", "कुकीज़"],
        "mithai": ["sweets", "मिठाई"],
        "ready to eat": ["instant meal", "तुरंत भोजन"],
        "rice": ["chawal", "चावल"],
        "wheat flour": ["atta", "आटा"],
        "lentils": ["dal", "दाल"],
        "mustard oil": ["sarson tel", "सरसों तेल"],
        "jaggery": ["gur", "गुड़"],
        "ghee": ["घी", "clarified butter"],
        "honey": ["शहद", "madhu"],
        "coir mat": ["narial coir mat", "कॉयर मैट"],
        "brass idol": ["पीतल मूर्ति", "brass murti"],
        "wooden craft": ["लकड़ी शिल्प", "wood craft"],
        "bamboo basket": ["बांस टोकरी", "cane basket"],
        "gift hamper": ["उपहार पैक", "gift pack"],
        "souvenir": ["yaadgaar", "यादगार"],
        "service package": ["seva package", "सेवा पैकेज"],
        "website development": ["web development", "वेबसाइट बनाना"],
        "digital marketing": ["online marketing", "डिजिटल मार्केटिंग"],
        "repair service": ["मरम्मत सेवा", "maintenance service"],
        "cleaning service": ["सफाई सेवा", "housekeeping service"],
        "consulting service": ["सलाह सेवा", "advisory service"],
    }

    business_terms = {
        "enterprise": ["udyam", "udyog", "उद्यम", "karobar", "व्यापार"],
        "registration": ["panjikaran", "पंजीकरण", "registration number"],
        "turnover": ["karobar", "bikri", "बिक्री", "annual sales"],
        "manufacturing": ["nirman", "निर्माण", "utpadan", "उत्पादन"],
        "wholesale": ["thok", "थोक", "bulk selling"],
        "retail": ["khudra", "खुदरा", "chhota dukaan"],
        "onboarding": ["shamil hona", "onboard", "ऑनबोर्डिंग"],
        "seller": ["vikreta", "seller partner", "विक्रेता"],
        "buyer": ["kharidar", "ग्राहक", "consumer"],
        "catalog": ["सूची", "product list", "listing"],
        "category": ["श्रेणी", "varg", "segment"],
        "classification": ["वर्गीकरण", "mapping"],
        "invoice": ["bill", "चालान"],
        "gst": ["gstin", "जीएसटी"],
        "hsn": ["hsn code", "एचएसएन"],
        "payment": ["bhugtan", "भुगतान"],
        "delivery": ["supurdagi", "डिलीवरी"],
        "logistics": ["transport", "लॉजिस्टिक्स"],
        "inventory": ["stock", "भंडार"],
        "warehouse": ["godown", "गोदाम"],
        "brand": ["marka", "ब्रांड"],
        "quality": ["gunvatta", "गुणवत्ता"],
        "compliance": ["anupalan", "अनुपालन"],
        "audit": ["लेखा जांच", "inspection"],
        "consent": ["sahmati", "सहमति"],
        "policy": ["नीति", "rule"],
        "analytics": ["vishleshan", "विश्लेषण"],
        "dashboard": ["प्रदर्श पटल", "control panel"],
        "marketplace": ["bazaar", "मार्केटप्लेस"],
        "commission": ["dalali", "कमीशन"],
        "subsidy": ["अनुदान", "support grant"],
        "loan": ["rin", "ऋण"],
        "credit": ["udhaar", "उधार"],
        "debit": ["jama", "डेबिट"],
        "profit": ["munafa", "मुनाफा"],
        "loss": ["nuksan", "नुकसान"],
        "export": ["niryaat", "निर्यात"],
        "import": ["aayaat", "आयात"],
        "state": ["rajya", "राज्य"],
        "district": ["zilla", "ज़िला"],
        "pincode": ["pin code", "postal code"],
        "certificate": ["praman patra", "प्रमाण पत्र"],
        "verification": ["satyaapan", "सत्यापन"],
        "application": ["aavedan", "आवेदन"],
        "approval": ["manzoori", "मंजूरी"],
    }

    unit_terms = {
        "kilogram": ["kg", "kilo", "किलो", "किलोग्राम"],
        "gram": ["gm", "g", "ग्राम"],
        "milligram": ["mg", "मिलीग्राम"],
        "quintal": ["qtl", "क्विंटल"],
        "ton": ["टन", "tonne"],
        "piece": ["piece", "pcs", "nag", "नग", "adad", "अदद"],
        "dozen": ["darjan", "दर्जन", "drz"],
        "liter": ["litre", "ltr", "लीटर"],
        "milliliter": ["ml", "मिलीलीटर"],
        "meter": ["mtr", "मीटर", "m"],
        "centimeter": ["cm", "सेमी"],
        "millimeter": ["mm", "मिमी"],
        "feet": ["ft", "फीट"],
        "inch": ["in", "इंच"],
        "pair": ["pr", "जोड़"],
        "pack": ["pkt", "पैक"],
        "box": ["bx", "डिब्बा"],
        "set": ["combo", "सेट"],
        "bundle": ["गट्ठा", "lot"],
        "unit": ["nos", "number", "इकाई"],
    }

    phonetic_variants = {
        "pickle": ["pikul", "pikal", "pikle"],
        "business": ["bijness", "biznes"],
        "category": ["catagory", "categry"],
        "organic": ["orgenik", "arganik"],
        "registration": ["rejistration", "ragistration"],
        "inventory": ["inwentry", "invantory"],
        "quantity": ["quantitty", "kwantity"],
        "commission": ["komission", "commision"],
    }

    for mapping in (product_terms, business_terms, unit_terms, phonetic_variants):
        for canonical, variants in mapping.items():
            _merge_entry(synonyms, canonical, [canonical, *variants])

    filler_terms = [
        "spice mix", "snack pack", "regional food", "fresh vegetables", "dairy products", "bakery goods",
        "tableware", "kitchen tools", "home decor", "furnishing", "mobile accessories", "home appliance",
        "health supplement", "fitness product", "medical essentials", "bath body", "hair styling",
        "farm tools", "irrigation", "handloom textiles", "gift articles", "office supplies", "school supplies",
        "women apparel", "men apparel", "kids apparel", "computer peripherals", "audio video", "fragrances",
        "packaged foods", "daily essentials", "bulk supplies", "personal care", "services", "construction",
        "pricing", "quality score", "activation", "seller support", "tech fit", "language support",
        "performance", "geography", "domain", "compliance check", "data governance", "privacy policy",
        "audit log", "admin dashboard", "voice input", "translation", "transcript", "taxonomy", "mapping table",
    ]
    for term in filler_terms:
        _merge_entry(synonyms, term, [term])

    return {k: sorted(set(v), key=v.index) for k, v in synonyms.items()}


DEFAULT_SYNONYMS: dict[str, list[str]] = _build_default_synonyms()
UNIT_CANONICALS = {
    "kilogram",
    "gram",
    "milligram",
    "quintal",
    "ton",
    "piece",
    "dozen",
    "liter",
    "milliliter",
    "meter",
    "centimeter",
    "millimeter",
    "feet",
    "inch",
    "pair",
    "pack",
    "box",
    "set",
    "bundle",
    "unit",
}


def _extract_synonyms_from_payload(payload: Any) -> dict[str, list[str]]:
    extracted: dict[str, list[str]] = {}
    if not isinstance(payload, dict):
        return extracted

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, list):
                    _merge_entry(extracted, str(key), [str(v) for v in value])
                elif isinstance(value, dict):
                    langs = [str(v) for v in value.values() if isinstance(v, str)]
                    if langs:
                        _merge_entry(extracted, str(key), langs)
                    _walk(value)
                elif isinstance(value, str):
                    _merge_entry(extracted, str(key), [value])
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return extracted


def _load_external_synonyms() -> dict[str, list[str]]:
    global _LOADED_EXTERNAL_SYNONYMS
    if _LOADED_EXTERNAL_SYNONYMS is not None:
        return _LOADED_EXTERNAL_SYNONYMS

    merged: dict[str, list[str]] = {}
    for path in (MSME_TERMS_PATH, PRODUCT_SYNONYMS_PATH):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        for canonical, variants in _extract_synonyms_from_payload(payload).items():
            _merge_entry(merged, canonical, variants)

    _LOADED_EXTERNAL_SYNONYMS = merged
    return merged


def _merged_synonyms(synonyms: dict[str, list[str]] | None) -> dict[str, list[str]]:
    if synonyms is not None:
        merged: dict[str, list[str]] = {}
        for canonical, variants in synonyms.items():
            _merge_entry(merged, canonical, [canonical, *variants])
        return merged

    merged = {k: list(v) for k, v in DEFAULT_SYNONYMS.items()}
    for canonical, variants in _load_external_synonyms().items():
        _merge_entry(merged, canonical, variants)
    return merged


def detect_language(text: str) -> str:
    """Detect rough language family from script usage."""
    if re.search(r"[\u0900-\u097F]", text or ""):
        return "hi"
    if re.search(r"[\u0B80-\u0BFF]", text or ""):
        return "ta"
    return "en"


def standardize_units(text: str) -> str:
    """Normalize unit variants to canonical unit labels."""
    normalized = text or ""
    mapping = _merged_synonyms(None)

    replacements: list[tuple[str, str]] = []
    for canonical, variants in mapping.items():
        if canonical in UNIT_CANONICALS:
            for variant in variants:
                if variant and variant != canonical:
                    replacements.append((variant, canonical))

    for variant, canonical in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(variant)}(?!\w)", flags=re.IGNORECASE)
        normalized = pattern.sub(canonical, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_product_terms(text: str) -> list[str]:
    """Extract known canonical product terms found in text."""
    raw = text or ""
    lower = raw.lower()
    vocabulary = _merged_synonyms(None)
    found: list[str] = []

    for canonical, variants in vocabulary.items():
        if canonical in UNIT_CANONICALS:
            continue
        candidates = [canonical, *variants]
        for token in sorted(set(candidates), key=len, reverse=True):
            if token and token in lower:
                found.append(canonical)
                break

    ordered: list[str] = []
    for term in found:
        if term not in ordered:
            ordered.append(term)
    return ordered


def normalize_transcript(text: str, synonyms: dict[str, list[str]] | None = None) -> str:
    """Normalize multilingual/transcribed terms to canonical English terms."""
    if not text:
        return text

    merged = _merged_synonyms(synonyms)
    normalized = standardize_units(text)

    replacements: list[tuple[str, str]] = []
    for canonical, variants in merged.items():
        for variant in [canonical, *variants]:
            variant_clean = str(variant or "").strip().lower()
            if variant_clean and variant_clean != canonical:
                replacements.append((variant_clean, canonical))

    for variant, canonical in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"(?<!\w){re.escape(variant)}(?!\w)", flags=re.IGNORECASE)
        normalized = pattern.sub(canonical, normalized)

    return re.sub(r"\s+", " ", normalized).strip()
