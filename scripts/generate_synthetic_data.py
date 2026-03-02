"""Generate synthetic datasets for VriddhiDisha analytics."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SEED = 2026
random.seed(SEED)
np.random.seed(SEED)

STATE_DISTRICTS: dict[str, list[str]] = {
    "Uttar Pradesh": ["Lucknow", "Kanpur Nagar", "Varanasi"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur"],
    "West Bengal": ["Kolkata", "Howrah", "Siliguri"],
    "Madhya Pradesh": ["Indore", "Bhopal", "Jabalpur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur"],
    "Karnataka": ["Bengaluru Urban", "Mysuru", "Belagavi"],
    "Gujarat": ["Ahmedabad", "Surat", "Rajkot"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Tirupati"],
    "Odisha": ["Khordha", "Cuttack", "Sambalpur"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
    "Kerala": ["Ernakulam", "Kozhikode", "Thiruvananthapuram"],
    "Jharkhand": ["Ranchi", "Dhanbad", "Jamshedpur"],
    "Assam": ["Kamrup Metro", "Dibrugarh", "Silchar"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar"],
    "Chhattisgarh": ["Raipur", "Bilaspur", "Durg"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat"],
    "Delhi": ["New Delhi", "North West Delhi", "South East Delhi"],
    "Jammu & Kashmir": ["Srinagar", "Jammu", "Anantnag"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Nainital"],
    "Himachal Pradesh": ["Shimla", "Kangra", "Mandi"],
    "Tripura": ["West Tripura", "Sepahijala", "Dhalai"],
    "Meghalaya": ["East Khasi Hills", "Ri-Bhoi", "West Garo Hills"],
    "Manipur": ["Imphal West", "Thoubal", "Churachandpur"],
    "Nagaland": ["Kohima", "Dimapur", "Mokokchung"],
    "Mizoram": ["Aizawl", "Lunglei", "Champhai"],
    "Arunachal Pradesh": ["Itanagar", "Tawang", "Pasighat"],
    "Goa": ["North Goa", "South Goa", "Mormugao"],
    "Sikkim": ["East Sikkim", "West Sikkim", "South Sikkim"],
    "Puducherry": ["Puducherry", "Karaikal", "Yanam"],
    "Chandigarh": ["Chandigarh", "Industrial Area", "Manimajra"],
    "Andaman & Nicobar": ["South Andaman", "North and Middle Andaman", "Nicobar"],
    "Dadra & Nagar Haveli": ["Dadra and Nagar Haveli", "Daman", "Diu"],
    "Lakshadweep": ["Kavaratti", "Agatti", "Minicoy"],
    "Ladakh": ["Leh", "Kargil", "Nubra"],
}

STATE_PROBABILITIES = {
    "Uttar Pradesh": 0.12,
    "Maharashtra": 0.10,
    "Bihar": 0.04,
    "West Bengal": 0.06,
    "Madhya Pradesh": 0.05,
    "Tamil Nadu": 0.07,
    "Rajasthan": 0.06,
    "Karnataka": 0.06,
    "Gujarat": 0.06,
    "Andhra Pradesh": 0.04,
    "Odisha": 0.03,
    "Telangana": 0.03,
    "Kerala": 0.04,
    "Jharkhand": 0.02,
    "Assam": 0.02,
    "Punjab": 0.02,
    "Chhattisgarh": 0.02,
    "Haryana": 0.02,
    "Delhi": 0.02,
    "Jammu & Kashmir": 0.01,
    "Uttarakhand": 0.01,
    "Himachal Pradesh": 0.01,
    "Tripura": 0.005,
    "Meghalaya": 0.005,
    "Manipur": 0.005,
    "Nagaland": 0.005,
    "Mizoram": 0.003,
    "Arunachal Pradesh": 0.003,
    "Goa": 0.005,
    "Sikkim": 0.002,
    "Puducherry": 0.002,
    "Chandigarh": 0.002,
    "Andaman & Nicobar": 0.001,
    "Dadra & Nagar Haveli": 0.001,
    "Lakshadweep": 0.001,
    "Ladakh": 0.001,
}

STATE_CODES = {
    "Rajasthan": "RJ",
    "Tamil Nadu": "TN",
    "Maharashtra": "MH",
    "Uttar Pradesh": "UP",
    "West Bengal": "WB",
    "Karnataka": "KA",
    "Gujarat": "GJ",
    "Kerala": "KL",
    "Madhya Pradesh": "MP",
    "Haryana": "HR",
    "Bihar": "BR",
    "Odisha": "OD",
    "Telangana": "TS",
    "Andhra Pradesh": "AP",
    "Assam": "AS",
    "Punjab": "PB",
    "Jharkhand": "JH",
    "Chhattisgarh": "CT",
    "Delhi": "DL",
    "Jammu & Kashmir": "JK",
    "Uttarakhand": "UK",
    "Himachal Pradesh": "HP",
    "Tripura": "TR",
    "Meghalaya": "ML",
    "Manipur": "MN",
    "Nagaland": "NL",
    "Mizoram": "MZ",
    "Arunachal Pradesh": "AR",
    "Goa": "GA",
    "Sikkim": "SK",
    "Puducherry": "PY",
    "Chandigarh": "CH",
    "Andaman & Nicobar": "AN",
    "Dadra & Nagar Haveli": "DN",
    "Lakshadweep": "LD",
    "Ladakh": "LA",
}

SECTOR_DISTRIBUTION = {
    "food": 0.25,
    "textiles": 0.15,
    "handicrafts": 0.12,
    "agriculture": 0.10,
    "services": 0.10,
    "electronics": 0.05,
    "health_beauty": 0.05,
    "others": 0.18,
}

SECTOR_META = {
    "food": {
        "nic": ("10", "10795", "Manufacture of papads, appalam and similar foods", "Manufacturing"),
        "category_l1": "Food & Beverage",
        "products": ["Mango Pickle", "Papad", "Masala Mix", "Ready-to-Eat Snacks"],
    },
    "textiles": {
        "nic": ("13", "13121", "Weaving, manufacture of cotton textiles", "Manufacturing"),
        "category_l1": "Fashion",
        "products": ["Cotton Saree", "Handloom Dupatta", "Kurta Fabric", "Silk Stole"],
    },
    "handicrafts": {
        "nic": ("32", "32909", "Other manufacturing n.e.c.", "Manufacturing"),
        "category_l1": "Handicrafts & Handloom",
        "products": ["Papier-mache Decor", "Brass Lamp", "Wooden Craft", "Terracotta Pot"],
    },
    "agriculture": {
        "nic": ("01", "01300", "Crop and animal production", "Manufacturing"),
        "category_l1": "Agriculture",
        "products": ["Vegetable Seeds", "Organic Fertilizer", "Compost", "Herbal Saplings"],
    },
    "services": {
        "nic": ("62", "62011", "Writing, modifying, testing of computer programs", "Services"),
        "category_l1": "Services",
        "products": ["Web Development", "Digital Marketing", "Catalog Design", "IT Support"],
    },
    "electronics": {
        "nic": ("26", "26101", "Manufacture of electronic components", "Manufacturing"),
        "category_l1": "Electronics",
        "products": ["LED Bulb", "Mobile Charger", "Earphones", "Power Adapter"],
    },
    "health_beauty": {
        "nic": ("20", "20232", "Manufacture of perfumes and toilet preparations", "Manufacturing"),
        "category_l1": "Beauty & Personal Care",
        "products": ["Herbal Face Pack", "Essential Oil", "Ayurvedic Balm", "Natural Soap"],
    },
    "others": {
        "nic": ("31", "31001", "Manufacture of furniture", "Manufacturing"),
        "category_l1": "Home & Kitchen",
        "products": ["Wooden Chair", "Storage Rack", "Kitchen Organizer", "Decorative Shelf"],
    },
}

SOCIAL_CATEGORIES = ["General", "OBC", "SC", "ST", "Minority"]
SOCIAL_PROBS = [0.40, 0.30, 0.15, 0.10, 0.05]

LANGUAGE_MAP = {
    "Uttar Pradesh": ["hi"],
    "Maharashtra": ["mr", "hi", "en"],
    "Bihar": ["hi"],
    "West Bengal": ["bn", "hi"],
    "Madhya Pradesh": ["hi"],
    "Tamil Nadu": ["ta", "en"],
    "Rajasthan": ["hi"],
    "Karnataka": ["kn", "en"],
    "Gujarat": ["gu", "hi"],
    "Andhra Pradesh": ["te", "en"],
    "Odisha": ["or", "hi"],
    "Telangana": ["te", "en"],
    "Kerala": ["ml", "en"],
    "Jharkhand": ["hi"],
    "Assam": ["as", "hi"],
    "Punjab": ["pa", "hi"],
    "Chhattisgarh": ["hi"],
    "Haryana": ["hi", "en"],
    "Delhi": ["hi", "en"],
    "Jammu & Kashmir": ["hi", "ur", "en"],
    "Uttarakhand": ["hi"],
    "Himachal Pradesh": ["hi"],
    "Tripura": ["bn", "hi"],
    "Meghalaya": ["en", "hi"],
    "Manipur": ["en", "hi"],
    "Nagaland": ["en", "hi"],
    "Mizoram": ["en", "hi"],
    "Arunachal Pradesh": ["en", "hi"],
    "Goa": ["en", "hi"],
    "Sikkim": ["en", "hi"],
    "Puducherry": ["ta", "en"],
    "Chandigarh": ["hi", "en"],
    "Andaman & Nicobar": ["hi", "en"],
    "Dadra & Nagar Haveli": ["hi", "gu"],
    "Lakshadweep": ["ml", "en"],
    "Ladakh": ["hi", "en"],
}


def _normalized_state_weights(states: list[str]) -> list[float]:
    raw = np.array([float(STATE_PROBABILITIES.get(state, 0.0)) for state in states], dtype=float)
    total = float(raw.sum())
    if total <= 0:
        return [1.0 / len(states) for _ in states]
    return (raw / total).tolist()


def _district_tier(district: str) -> int:
    tier1 = {
        "Jaipur", "Chennai", "Mumbai", "Lucknow", "Kolkata", "Bengaluru Urban", "Ahmedabad", "Ernakulam",
        "Indore", "Gurugram", "Patna", "Hyderabad", "Visakhapatnam", "New Delhi", "Pune", "Coimbatore",
    }
    tier2 = {
        "Jodhpur", "Madurai", "Nagpur", "Kanpur Nagar", "Howrah", "Mysuru", "Surat", "Kozhikode", "Bhopal",
        "Faridabad", "Cuttack", "Warangal", "Ludhiana", "Raipur", "Ranchi", "Srinagar", "Dehradun", "Shimla",
    }
    if district in tier1:
        return 1
    if district in tier2:
        return 2
    return 3


def generate_mse_profiles(n: int = 5000) -> pd.DataFrame:
    """Generate synthetic MSE profiles with realistic demographic and sector distribution."""
    states = list(STATE_DISTRICTS.keys())
    probs = _normalized_state_weights(states)
    state_choices = np.random.choice(states, size=n, replace=True, p=probs)
    sectors = np.random.choice(
        list(SECTOR_DISTRIBUTION.keys()),
        size=n,
        p=list(SECTOR_DISTRIBUTION.values()),
    )

    women_flags = np.array([True] * (n // 2) + [False] * (n - n // 2))
    np.random.shuffle(women_flags)

    month_bins = [1, 2, 3, 4, 5, 6]
    month_weights = [0.12, 0.14, 0.16, 0.18, 0.19, 0.21]
    registration_month = np.random.choice(month_bins, size=n, p=month_weights)

    rows: list[dict[str, Any]] = []
    for idx in range(n):
        state = str(state_choices[idx])
        district = random.choice(STATE_DISTRICTS[state])
        tier = _district_tier(district)
        sector = str(sectors[idx])
        nic_2, nic_5, nic_desc, major_activity = SECTOR_META[sector]["nic"]
        category_l1 = SECTOR_META[sector]["category_l1"]
        products_pool = SECTOR_META[sector]["products"]
        products = random.sample(products_pool, k=min(len(products_pool), random.randint(1, 3)))
        is_women_owned = bool(women_flags[idx])
        owner_gender = "Female" if is_women_owned else random.choice(["Male", "Male", "Other"])
        social_category = np.random.choice(SOCIAL_CATEGORIES, p=SOCIAL_PROBS)
        language_preference = random.choice(LANGUAGE_MAP[state])
        enterprise_type = random.choice(["Micro", "Micro", "Small"])

        turnover = round(
            random.uniform(8.0, 95.0) if enterprise_type == "Micro" else random.uniform(100.0, 980.0),
            2,
        )
        investment = round(
            random.uniform(2.0, 48.0) if enterprise_type == "Micro" else random.uniform(50.0, 360.0),
            2,
        )

        month = int(registration_month[idx])
        base_catalog = 0.62 + (month - 1) * 0.05
        base_match = 0.70 + (month - 1) * 0.03
        base_live = 0.62 + (month - 1) * 0.04
        base_first = 0.38 + (month - 1) * 0.04

        if is_women_owned:
            base_catalog -= 0.06
        if category_l1 == "Food & Beverage":
            base_match += 0.08
        if category_l1 == "Handicrafts & Handloom":
            base_match -= 0.14
        if state in {"Tamil Nadu", "Karnataka", "Kerala"}:
            base_catalog += 0.05
            base_live += 0.04
        if state == "Rajasthan":
            base_live -= 0.10

        catalog_created = random.random() < min(max(base_catalog, 0.08), 0.95)
        snp_matched = catalog_created and (random.random() < min(max(base_match, 0.05), 0.96))
        live = snp_matched and (random.random() < min(max(base_live, 0.05), 0.93))
        first_order = live and (random.random() < min(max(base_first, 0.03), 0.88))

        district_code = (STATE_DISTRICTS[state].index(district) + 1) % 100
        udyam_number = f"UDYAM-{STATE_CODES[state]}-{district_code:02d}-{idx + 1:07d}"

        rows.append(
            {
                "mse_id": f"MSE{idx + 1:05d}",
                "udyam_number": udyam_number,
                "enterprise_name": f"{district} Enterprise {idx + 1}",
                "owner_name": f"Owner {idx + 1}",
                "owner_gender": owner_gender,
                "is_women_owned": int(is_women_owned),
                "enterprise_type": enterprise_type,
                "major_activity": major_activity,
                "state": state,
                "district": district,
                "tier": tier,
                "social_category": str(social_category),
                "nic_2digit": nic_2,
                "nic_5digit": nic_5,
                "nic_description": nic_desc,
                "sector": sector,
                "category_l1": category_l1,
                "language_preference": language_preference,
                "turnover_lakh": turnover,
                "investment_lakh": investment,
                "products_services": "|".join(products),
                "registration_month": month,
                "registered": 1,
                "catalog_created": int(catalog_created),
                "snp_matched": int(snp_matched),
                "live": int(live),
                "first_order": int(first_order),
            }
        )

    return pd.DataFrame(rows)


def generate_products(n: int = 2000, mse_profiles: pd.DataFrame | None = None) -> pd.DataFrame:
    """Generate synthetic product listings linked to MSE profiles."""
    if mse_profiles is None:
        mse_profiles = generate_mse_profiles()

    products: list[dict[str, Any]] = []
    by_mse_count: dict[str, int] = defaultdict(int)
    candidates = mse_profiles.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    idx = 0

    while len(products) < n and idx < len(candidates) * 8:
        row = candidates.iloc[idx % len(candidates)]
        mse_id = str(row["mse_id"])
        if by_mse_count[mse_id] >= 5:
            idx += 1
            continue

        category_l1 = str(row["category_l1"])
        sector = str(row["sector"])
        product_name = random.choice(SECTOR_META[sector]["products"])
        quantity = random.choice(["200 gram", "500 gram", "1 kg", "1 piece", "2 piece", "250 ml"])

        price_base = {
            "Food & Beverage": (80, 420),
            "Fashion": (350, 3200),
            "Handicrafts & Handloom": (250, 4500),
            "Agriculture": (60, 1200),
            "Services": (300, 6000),
            "Electronics": (250, 9000),
            "Beauty & Personal Care": (120, 1800),
            "Home & Kitchen": (180, 3500),
        }.get(category_l1, (100, 2200))
        price = round(random.uniform(*price_base), 2)

        products.append(
            {
                "product_id": f"PROD{len(products) + 1:05d}",
                "mse_id": mse_id,
                "state": row["state"],
                "district": row["district"],
                "category_l1": category_l1,
                "category_l2": _default_l2(category_l1),
                "product_name": product_name,
                "description": f"{product_name} by {row['enterprise_name']} in {row['district']}.",
                "price": price,
                "quantity": quantity,
                "is_handmade": int(sector in {"handicrafts", "food", "textiles"}),
            }
        )
        by_mse_count[mse_id] += 1
        idx += 1

    return pd.DataFrame(products)


def generate_onboarding_funnel(mse_profiles: pd.DataFrame, months: int = 6) -> pd.DataFrame:
    """Generate state-month funnel summary with trend and pattern injection."""
    month_targets = {
        1: {"registered": 800, "catalog_created": 500, "snp_matched": 350, "live": 200, "first_order": 80},
        2: {"registered": 900, "catalog_created": 600, "snp_matched": 420, "live": 280, "first_order": 130},
        3: {"registered": 1000, "catalog_created": 720, "snp_matched": 540, "live": 390, "first_order": 210},
        4: {"registered": 1080, "catalog_created": 810, "snp_matched": 630, "live": 470, "first_order": 270},
        5: {"registered": 1120, "catalog_created": 880, "snp_matched": 710, "live": 540, "first_order": 330},
        6: {"registered": 1200, "catalog_created": 950, "snp_matched": 780, "live": 600, "first_order": 380},
    }

    states = list(STATE_DISTRICTS.keys())
    weights = _normalized_state_weights(states)
    state_weights = dict(zip(states, weights))

    rows: list[dict[str, Any]] = []
    for month in range(1, months + 1):
        target = month_targets.get(month, month_targets[6])
        for state, weight in state_weights.items():
            reg = int(round(target["registered"] * weight))
            cat = int(round(target["catalog_created"] * weight))
            snp = int(round(target["snp_matched"] * weight))
            live = int(round(target["live"] * weight))
            first = int(round(target["first_order"] * weight))

            if state in {"Tamil Nadu", "Karnataka", "Kerala", "Telangana"}:
                cat = int(cat * 1.05)
                live = int(live * 1.06)
            if state == "Rajasthan":
                reg = int(reg * 1.08)
                live = int(live * 0.88)

            women_registered = int(reg * 0.50)
            women_catalog_created = int(cat * 0.45)

            rows.append(
                {
                    "month": month,
                    "state": state,
                    "registered": max(reg, 0),
                    "catalog_created": max(min(cat, reg), 0),
                    "snp_matched": max(min(snp, cat), 0),
                    "live": max(min(live, snp), 0),
                    "first_order": max(min(first, live), 0),
                    "women_registered": women_registered,
                    "women_catalog_created": women_catalog_created,
                }
            )

    return pd.DataFrame(rows)


def generate_snp_assignments(mse_profiles: pd.DataFrame, snp_database: list[dict[str, Any]]) -> pd.DataFrame:
    """Generate realistic MSE-SNP assignments for live MSEs with score outputs."""
    if not snp_database:
        return pd.DataFrame(columns=["mse_id", "snp_id", "state", "category_l1", "match_score", "rank"])

    live_mses = mse_profiles[mse_profiles["live"] == 1]
    assignments: list[dict[str, Any]] = []

    for _, mse in live_mses.iterrows():
        state = str(mse["state"])
        category = str(mse["category_l1"])
        candidates = []
        for snp in snp_database:
            categories = snp.get("supported_categories", [])
            coverage = [str(x).lower() for x in snp.get("geographic_coverage", [])]
            supports_category = category in categories
            covers_state = state.lower() in coverage or "all india" in coverage or "pan-india" in coverage or "pan india" in coverage
            if supports_category and covers_state:
                candidates.append(snp)

        if not candidates:
            candidates = [s for s in snp_database if category in s.get("supported_categories", [])] or snp_database

        candidates = sorted(
            candidates,
            key=lambda s: (
                float(s.get("seller_success_rate", 0.6)),
                -float(s.get("commission_rate", 10.0)),
            ),
            reverse=True,
        )
        selected = candidates[0]
        match_score = round(random.uniform(0.62, 0.94), 4)

        assignments.append(
            {
                "mse_id": mse["mse_id"],
                "snp_id": selected.get("snp_id", "SNP000"),
                "state": state,
                "category_l1": category,
                "match_score": match_score,
                "rank": 1,
            }
        )

    return pd.DataFrame(assignments)


def _default_l2(category_l1: str) -> str:
    mapping = {
        "Food & Beverage": "Packaged Foods",
        "Fashion": "Women's Apparel",
        "Handicrafts & Handloom": "Crafts",
        "Agriculture": "Seeds",
        "Services": "Digital Services",
        "Electronics": "Mobile & Accessories",
        "Beauty & Personal Care": "Skincare",
        "Home & Kitchen": "Home Decor",
    }
    return mapping.get(category_l1, "General")


def generate() -> dict[str, int]:
    """Generate all synthetic datasets and persist to data/synthetic."""
    data_dir = Path(__file__).resolve().parents[1] / "data" / "synthetic"
    data_dir.mkdir(parents=True, exist_ok=True)

    mse_profiles = generate_mse_profiles(5000)
    products = generate_products(2000, mse_profiles)
    funnel = generate_onboarding_funnel(mse_profiles, months=6)

    snp_path = Path(__file__).resolve().parents[1] / "data" / "snp_profiles" / "snp_database.json"
    try:
        snp_database = json.loads(snp_path.read_text(encoding="utf-8"))
        if not isinstance(snp_database, list):
            snp_database = []
    except (OSError, json.JSONDecodeError):
        snp_database = []

    assignments = generate_snp_assignments(mse_profiles, snp_database)

    mse_profiles.to_csv(data_dir / "mse_profiles.csv", index=False)
    products.to_csv(data_dir / "products.csv", index=False)
    funnel.to_csv(data_dir / "onboarding_funnel.csv", index=False)
    assignments.to_csv(data_dir / "snp_assignments.csv", index=False)

    return {
        "mse_profiles": len(mse_profiles),
        "products": len(products),
        "funnel_rows": len(funnel),
        "assignments": len(assignments),
    }


if __name__ == "__main__":
    output = generate()
    print(output)
    print(f"Data directory: {Path(__file__).resolve().parents[1] / 'data' / 'synthetic'}")
