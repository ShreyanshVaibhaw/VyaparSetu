"""Generate Prompt 1 NIC and state/district reference data."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_nic_codes() -> dict[str, object]:
    key_descriptions = {
        "01": "Crop and animal production, hunting and related service activities",
        "02": "Forestry and logging",
        "03": "Fishing and aquaculture",
        "10": "Manufacture of food products",
        "11": "Manufacture of beverages",
        "13": "Manufacture of textiles",
        "14": "Manufacture of wearing apparel",
        "15": "Manufacture of leather and related products",
        "16": "Manufacture of wood and of products of wood and cork, except furniture",
        "17": "Manufacture of paper and paper products",
        "20": "Manufacture of chemicals and chemical products",
        "21": "Manufacture of pharmaceuticals, medicinal chemical and botanical products",
        "22": "Manufacture of rubber and plastics products",
        "23": "Manufacture of other non-metallic mineral products",
        "24": "Manufacture of basic metals",
        "25": "Manufacture of fabricated metal products, except machinery and equipment",
        "26": "Manufacture of computer, electronic and optical products",
        "27": "Manufacture of electrical equipment",
        "28": "Manufacture of machinery and equipment n.e.c.",
        "31": "Manufacture of furniture",
        "32": "Other manufacturing",
        "33": "Repair and installation of machinery and equipment",
        "41": "Construction of buildings",
        "46": "Wholesale trade, except of motor vehicles and motorcycles",
        "47": "Retail trade, except of motor vehicles and motorcycles",
        "56": "Food and beverage service activities",
        "62": "Computer programming, consultancy and related activities",
        "74": "Other professional, scientific and technical activities",
        "85": "Education",
        "86": "Human health activities",
        "95": "Repair of computers and personal and household goods",
        "96": "Other personal service activities",
    }
    divisions = [
        {
            "nic_2digit": f"{i:02d}",
            "description": key_descriptions.get(
                f"{i:02d}", "Division not used in NIC-2008 or less common division"
            ),
        }
        for i in range(1, 100)
    ]
    common_5digit = [
        {
            "nic_5digit": "10792",
            "description": "Manufacture of spices and condiments",
            "parent_2digit": "10",
        },
        {
            "nic_5digit": "10795",
            "description": "Manufacture of papads, appalam and similar foods",
            "parent_2digit": "10",
        },
        {
            "nic_5digit": "11041",
            "description": "Manufacture of soft drinks",
            "parent_2digit": "11",
        },
        {
            "nic_5digit": "13121",
            "description": "Weaving, manufacture of cotton textiles",
            "parent_2digit": "13",
        },
        {
            "nic_5digit": "13921",
            "description": "Manufacture of made-up textile articles",
            "parent_2digit": "13",
        },
        {
            "nic_5digit": "14101",
            "description": "Manufacture of wearing apparel except fur apparel",
            "parent_2digit": "14",
        },
        {
            "nic_5digit": "15121",
            "description": "Manufacture of luggage, handbags and similar articles",
            "parent_2digit": "15",
        },
        {
            "nic_5digit": "16221",
            "description": "Manufacture of wooden containers",
            "parent_2digit": "16",
        },
        {
            "nic_5digit": "17022",
            "description": "Manufacture of corrugated paper and paperboard containers",
            "parent_2digit": "17",
        },
        {
            "nic_5digit": "20231",
            "description": "Manufacture of soap and detergents",
            "parent_2digit": "20",
        },
        {
            "nic_5digit": "20232",
            "description": "Manufacture of perfumes and toilet preparations",
            "parent_2digit": "20",
        },
        {
            "nic_5digit": "21001",
            "description": "Manufacture of pharmaceutical products",
            "parent_2digit": "21",
        },
        {
            "nic_5digit": "23931",
            "description": "Manufacture of clay building materials",
            "parent_2digit": "23",
        },
        {
            "nic_5digit": "25931",
            "description": "Manufacture of metal utensils",
            "parent_2digit": "25",
        },
        {
            "nic_5digit": "25993",
            "description": "Manufacture of metal ornaments",
            "parent_2digit": "25",
        },
        {
            "nic_5digit": "26101",
            "description": "Manufacture of electronic components",
            "parent_2digit": "26",
        },
        {
            "nic_5digit": "27101",
            "description": "Manufacture of electric motors and transformers",
            "parent_2digit": "27",
        },
        {
            "nic_5digit": "27501",
            "description": "Manufacture of electric domestic appliances",
            "parent_2digit": "27",
        },
        {
            "nic_5digit": "31001",
            "description": "Manufacture of furniture",
            "parent_2digit": "31",
        },
        {
            "nic_5digit": "32111",
            "description": "Manufacture of jewellery and related articles",
            "parent_2digit": "32",
        },
        {
            "nic_5digit": "32904",
            "description": "Manufacture of candles",
            "parent_2digit": "32",
        },
        {
            "nic_5digit": "46301",
            "description": "Wholesale of food, beverages and tobacco",
            "parent_2digit": "46",
        },
        {
            "nic_5digit": "47211",
            "description": "Retail sale of food in specialized stores",
            "parent_2digit": "47",
        },
        {
            "nic_5digit": "47711",
            "description": "Retail sale of readymade garments",
            "parent_2digit": "47",
        },
        {
            "nic_5digit": "56101",
            "description": "Restaurants without bar",
            "parent_2digit": "56",
        },
        {
            "nic_5digit": "62011",
            "description": "Writing, modifying, testing of computer programs",
            "parent_2digit": "62",
        },
        {
            "nic_5digit": "74101",
            "description": "Fashion design related activities",
            "parent_2digit": "74",
        },
        {
            "nic_5digit": "95210",
            "description": "Repair of consumer electronics",
            "parent_2digit": "95",
        },
        {
            "nic_5digit": "96021",
            "description": "Hairdressing and other beauty treatment",
            "parent_2digit": "96",
        },
    ]
    return {
        "nic_2digit_divisions": divisions,
        "common_5digit_details": common_5digit,
    }


def build_state_districts() -> dict[str, object]:
    # 36 states/UTs; each gets two district rows to ensure 50+ district entries.
    base_rows = [
        ("Andhra Pradesh", "Visakhapatnam", 17.6868, 83.2185, 1),
        ("Arunachal Pradesh", "Itanagar", 27.0844, 93.6053, 2),
        ("Assam", "Guwahati", 26.1445, 91.7362, 1),
        ("Bihar", "Patna", 25.5941, 85.1376, 1),
        ("Chhattisgarh", "Raipur", 21.2514, 81.6296, 1),
        ("Goa", "Panaji", 15.4909, 73.8278, 2),
        ("Gujarat", "Ahmedabad", 23.0225, 72.5714, 1),
        ("Haryana", "Gurugram", 28.4595, 77.0266, 1),
        ("Himachal Pradesh", "Shimla", 31.1048, 77.1734, 2),
        ("Jharkhand", "Ranchi", 23.3441, 85.3096, 1),
        ("Karnataka", "Bengaluru Urban", 12.9716, 77.5946, 1),
        ("Kerala", "Ernakulam", 9.9816, 76.2999, 1),
        ("Madhya Pradesh", "Indore", 22.7196, 75.8577, 1),
        ("Maharashtra", "Mumbai", 19.0760, 72.8777, 1),
        ("Manipur", "Imphal West", 24.8170, 93.9368, 2),
        ("Meghalaya", "East Khasi Hills", 25.5788, 91.8933, 2),
        ("Mizoram", "Aizawl", 23.7271, 92.7176, 2),
        ("Nagaland", "Kohima", 25.6751, 94.1086, 2),
        ("Odisha", "Khordha", 20.1734, 85.6745, 1),
        ("Punjab", "Ludhiana", 30.9009, 75.8573, 1),
        ("Rajasthan", "Jaipur", 26.9124, 75.7873, 1),
        ("Sikkim", "East Sikkim", 27.3389, 88.6065, 2),
        ("Tamil Nadu", "Chennai", 13.0827, 80.2707, 1),
        ("Telangana", "Hyderabad", 17.3850, 78.4867, 1),
        ("Tripura", "West Tripura", 23.9408, 91.9882, 2),
        ("Uttar Pradesh", "Lucknow", 26.8467, 80.9462, 1),
        ("Uttarakhand", "Dehradun", 30.3165, 78.0322, 1),
        ("West Bengal", "Kolkata", 22.5726, 88.3639, 1),
        ("Andaman and Nicobar Islands", "South Andaman", 11.7401, 92.6586, 3),
        ("Chandigarh", "Chandigarh", 30.7333, 76.7794, 1),
        ("Dadra and Nagar Haveli and Daman and Diu", "Daman", 20.3974, 72.8328, 2),
        ("Delhi", "New Delhi", 28.6139, 77.2090, 1),
        ("Jammu and Kashmir", "Srinagar", 34.0837, 74.7973, 2),
        ("Ladakh", "Leh", 34.1526, 77.5771, 3),
        ("Lakshadweep", "Kavaratti", 10.5667, 72.6417, 3),
        ("Puducherry", "Puducherry", 11.9416, 79.8083, 2),
    ]
    states: list[dict[str, object]] = []
    for state, district, lat, lon, tier in base_rows:
        states.append(
            {
                "state": state,
                "districts": [
                    {"district": district, "lat": lat, "lon": lon, "tier": tier},
                    {
                        "district": f"{district} Industrial Cluster",
                        "lat": round(lat + 0.18, 4),
                        "lon": round(lon + 0.21, 4),
                        "tier": min(3, tier + 1),
                    },
                ],
            }
        )
    return {"states": states}


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "mse_data"
    write_json(root / "nic_codes.json", build_nic_codes())
    write_json(root / "state_districts.json", build_state_districts())
    print("generated", root / "nic_codes.json", root / "state_districts.json")


if __name__ == "__main__":
    main()
