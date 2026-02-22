"""Generate Prompt 1 sample Udyam records."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "data" / "mse_data" / "sample_udyam_records.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        ("UDYAM-RJ-08-0001543", "Maru Mahila Foods", "Kavita Choudhary", "Female", "Micro", "Manufacturing", "10", "10795", "Manufacture of papads, appalam and similar foods", "Rajasthan", "Jodhpur", "342001", "Basni Industrial Area, Jodhpur", "OBC", "hi", True, ["Papad", "Pickle", "Masala"]),
        ("UDYAM-TN-33-0012451", "Kanchi Loom Collective", "Meenakshi R", "Female", "Small", "Manufacturing", "13", "13121", "Weaving, manufacture of cotton textiles", "Tamil Nadu", "Chennai", "600001", "Kanchipuram Handloom Cluster", "General", "ta", True, ["Handloom Saree", "Cotton Dupatta", "Stoles"]),
        ("UDYAM-KL-32-0007321", "Malabar Spice Works", "Niyas K", "Male", "Micro", "Manufacturing", "10", "10792", "Manufacture of spices and condiments", "Kerala", "Kozhikode", "673001", "Kozhikode Spice Market", "General", "en", False, ["Black Pepper", "Cardamom", "Turmeric Powder"]),
        ("UDYAM-UP-09-0034567", "Awadh Handcraft Studio", "Raju Vishwakarma", "Male", "Micro", "Manufacturing", "32", "32909", "Other manufacturing n.e.c.", "Uttar Pradesh", "Lucknow", "226001", "Chowk Artisans Lane", "SC", "hi", False, ["Chikan Embroidery", "Handcrafted Home Decor"]),
        ("UDYAM-WB-19-0041122", "Kolkata Leather Line", "Asif Karim", "Male", "Small", "Manufacturing", "15", "15121", "Manufacture of luggage, handbags and similar articles", "West Bengal", "Kolkata", "700001", "Tangra Leather Hub", "OBC", "bn", False, ["Leather Bags", "Wallets", "Belts"]),
        ("UDYAM-UP-09-0078901", "Moradabad Brass Udyog", "Imran Ali", "Male", "Small", "Manufacturing", "25", "25931", "Manufacture of metal utensils", "Uttar Pradesh", "Moradabad", "244001", "Peetal Nagri, Moradabad", "General", "hi", False, ["Brass Utensils", "Brass Decor", "Lamps"]),
        ("UDYAM-KA-29-0019988", "Bengaluru Byte Services", "Nandini Rao", "Female", "Small", "Services", "62", "62011", "Writing, modifying, testing of computer programs", "Karnataka", "Bengaluru Urban", "560001", "Indiranagar, Bengaluru", "General", "kn", True, ["Web Development", "Marketplace Integration"]),
        ("UDYAM-GJ-24-0023432", "Shree Athaana Gruh", "Hetal Patel", "Female", "Micro", "Manufacturing", "10", "10792", "Manufacture of spices and condiments", "Gujarat", "Ahmedabad", "380001", "Naroda GIDC, Ahmedabad", "General", "gu", True, ["Mango Pickle", "Lemon Pickle", "Masala Mix"]),
        ("UDYAM-WB-19-0067321", "Nadi Jute Creations", "Sutapa Das", "Female", "Micro", "Manufacturing", "13", "13921", "Manufacture of made-up textile articles", "West Bengal", "Howrah", "711101", "Howrah Jute Cluster", "OBC", "bn", True, ["Jute Bags", "Jute File Folders", "Eco Gift Packs"]),
        ("UDYAM-UP-09-0039981", "Saharanpur Woodcraft", "Harish Malik", "Male", "Small", "Manufacturing", "16", "16221", "Manufacture of wooden containers", "Uttar Pradesh", "Saharanpur", "247001", "Wood Craft Zone, Saharanpur", "General", "hi", False, ["Wooden Furniture", "Carved Panels"]),
        ("UDYAM-UP-09-0057789", "Khurja Mitti Kala", "Suman Prajapati", "Female", "Micro", "Manufacturing", "23", "23931", "Manufacture of clay building materials", "Uttar Pradesh", "Bulandshahr", "203131", "Pottery Road, Khurja", "OBC", "hi", True, ["Ceramic Bowls", "Planters", "Tea Sets"]),
        ("UDYAM-DL-07-0016677", "Wazirpur Steel House", "Rajesh Arora", "Male", "Small", "Manufacturing", "25", "25931", "Manufacture of metal utensils", "Delhi", "North West Delhi", "110052", "Wazirpur Industrial Area", "General", "hi", False, ["Steel Utensils", "Kitchen Storage"]),
        ("UDYAM-SK-11-0001122", "Sikkim Organic Valley", "Tenzing Lepcha", "Male", "Micro", "Manufacturing", "01", "01300", "Crop and animal production", "Sikkim", "East Sikkim", "737101", "Gangtok Organic Cluster", "ST", "en", False, ["Organic Vegetables", "Herbal Tea"]),
        ("UDYAM-RJ-08-0009987", "Bikaner Papad Kendra", "Rekha Bansal", "Female", "Micro", "Manufacturing", "10", "10795", "Manufacture of papads, appalam and similar foods", "Rajasthan", "Jaipur", "302001", "Bani Park, Jaipur", "General", "hi", True, ["Papad", "Fryums", "Masala Papad Mix"]),
        ("UDYAM-UP-09-0043210", "Lucknow Zardozi Works", "Amina Siddiqui", "Female", "Micro", "Manufacturing", "13", "13921", "Manufacture of made-up textile articles", "Uttar Pradesh", "Lucknow", "226018", "Aminabad, Lucknow", "OBC", "hi", True, ["Embroidery Saree", "Zardozi Dupatta"]),
        ("UDYAM-RJ-08-0022110", "Jaipur Blockprint Hub", "Rohit Saini", "Male", "Small", "Manufacturing", "13", "13131", "Finishing of cotton and blended textiles", "Rajasthan", "Jaipur", "302012", "Sanganer, Jaipur", "General", "hi", False, ["Block Print Fabric", "Table Linen"]),
        ("UDYAM-JK-01-0007765", "Kashmir Papier Art", "Irfan Bhat", "Male", "Micro", "Manufacturing", "32", "32909", "Other manufacturing n.e.c.", "Jammu and Kashmir", "Srinagar", "190001", "Nawa Kadal, Srinagar", "General", "en", False, ["Papier-mâché Boxes", "Decorative Trays"]),
        ("UDYAM-KL-32-0005544", "Alleppey Coir Mahila", "Latha Menon", "Female", "Micro", "Manufacturing", "13", "13921", "Manufacture of made-up textile articles", "Kerala", "Ernakulam", "682001", "Coir Park, Kochi", "General", "en", True, ["Coir Mats", "Coir Ropes"]),
        ("UDYAM-KA-29-0031122", "Mysuru Sugandh", "Sahana B", "Female", "Micro", "Manufacturing", "32", "32904", "Manufacture of candles", "Karnataka", "Mysuru", "570001", "Nanjangud Road, Mysuru", "OBC", "kn", True, ["Agarbatti", "Dhoop", "Pooja Kits"]),
        ("UDYAM-UP-09-0088811", "Moradabad Heritage Brass", "Faizan Khan", "Male", "Small", "Manufacturing", "25", "25993", "Manufacture of metal ornaments", "Uttar Pradesh", "Moradabad", "244001", "Galshaheed, Moradabad", "General", "hi", False, ["Brassware", "Decor Lamps"]),
    ]

    items = []
    for idx, row in enumerate(rows, start=1):
        (
            udyam_number,
            enterprise_name,
            owner_name,
            owner_gender,
            enterprise_type,
            major_activity,
            nic_2digit,
            nic_5digit,
            nic_description,
            state,
            district,
            pincode,
            address,
            social_category,
            language_preference,
            is_women_owned,
            products_services,
        ) = row
        items.append(
            {
                "udyam_number": udyam_number,
                "enterprise_name": enterprise_name,
                "owner_name": owner_name,
                "owner_gender": owner_gender,
                "enterprise_type": enterprise_type,
                "major_activity": major_activity,
                "nic_2digit": nic_2digit,
                "nic_5digit": nic_5digit,
                "nic_description": nic_description,
                "state": state,
                "district": district,
                "pincode": pincode,
                "address": address,
                "mobile": f"+91980000{idx:04d}",
                "email": f"contact{idx}@{enterprise_name.lower().replace(' ', '')}.in",
                "date_of_incorporation": f"201{idx % 10}-0{(idx % 9) + 1}-15",
                "date_of_udyam": f"202{idx % 6}-0{(idx % 9) + 1}-20",
                "investment_plant": round(2.5 + idx * 1.3, 2),
                "turnover": round(18 + idx * 27.5, 2),
                "gstin": f"{int(idx % 36) + 1:02d}ABCDE{idx:04d}F1Z{idx % 9}",
                "pan": f"ABCDE{idx:04d}F",
                "social_category": social_category,
                "is_women_owned": is_women_owned,
                "language_preference": language_preference,
                "products_services": products_services,
            }
        )

    out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print("generated", out, len(items))


if __name__ == "__main__":
    main()
