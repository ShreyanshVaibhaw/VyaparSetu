"""Udyam fetching and mock profile generation."""

from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from config import UDYAM_API_URL
from src.common.models import MSEProfile


class UdyamFetcher:
    """Fetch MSE data via Udyam number with resilient demo fallback."""

    UDYAM_PATTERN = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")

    STATE_CODE_TO_NAME = {
        "AN": "Andaman and Nicobar Islands",
        "AP": "Andhra Pradesh",
        "AR": "Arunachal Pradesh",
        "AS": "Assam",
        "BR": "Bihar",
        "CH": "Chandigarh",
        "CG": "Chhattisgarh",
        "DN": "Dadra and Nagar Haveli and Daman and Diu",
        "DD": "Dadra and Nagar Haveli and Daman and Diu",
        "DL": "Delhi",
        "GA": "Goa",
        "GJ": "Gujarat",
        "HR": "Haryana",
        "HP": "Himachal Pradesh",
        "JK": "Jammu and Kashmir",
        "JH": "Jharkhand",
        "KA": "Karnataka",
        "KL": "Kerala",
        "LA": "Ladakh",
        "LD": "Lakshadweep",
        "MP": "Madhya Pradesh",
        "MH": "Maharashtra",
        "MN": "Manipur",
        "ML": "Meghalaya",
        "MZ": "Mizoram",
        "NL": "Nagaland",
        "OD": "Odisha",
        "OR": "Odisha",
        "PY": "Puducherry",
        "PB": "Punjab",
        "RJ": "Rajasthan",
        "SK": "Sikkim",
        "TN": "Tamil Nadu",
        "TS": "Telangana",
        "TR": "Tripura",
        "UP": "Uttar Pradesh",
        "UK": "Uttarakhand",
        "UA": "Uttarakhand",
        "WB": "West Bengal",
    }

    DISTRICT_BY_STATE = {
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Bikaner"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruppur"],
        "Karnataka": ["Bengaluru Urban", "Mysuru", "Hubballi", "Belagavi"],
        "Maharashtra": ["Mumbai", "Pune", "Nashik", "Nagpur"],
        "Uttar Pradesh": ["Lucknow", "Moradabad", "Varanasi", "Kanpur Nagar"],
        "Gujarat": ["Ahmedabad", "Surat", "Rajkot", "Vadodara"],
        "Kerala": ["Ernakulam", "Kozhikode", "Thiruvananthapuram", "Thrissur"],
        "Delhi": ["New Delhi", "North West Delhi", "South West Delhi"],
    }

    NIC_OPTIONS = [
        ("10", "10792", "Manufacture of spices and condiments", "Manufacturing"),
        ("10", "10795", "Manufacture of papads, appalam and similar foods", "Manufacturing"),
        ("13", "13121", "Weaving, manufacture of cotton textiles", "Manufacturing"),
        ("14", "14101", "Manufacture of wearing apparel except fur apparel", "Manufacturing"),
        ("15", "15121", "Manufacture of luggage, handbags and similar articles", "Manufacturing"),
        ("25", "25931", "Manufacture of metal utensils", "Manufacturing"),
        ("32", "32909", "Other manufacturing n.e.c.", "Manufacturing"),
        ("62", "62011", "Writing, modifying, testing of computer programs", "Services"),
    ]

    PRODUCT_HINTS = {
        "10792": ["Spices", "Masala Mix", "Seasoning"],
        "10795": ["Papad", "Pickle", "Ready-to-Eat Snacks"],
        "13121": ["Cotton Saree", "Handloom Fabric", "Dupatta"],
        "14101": ["Kurta", "Shirt", "Dress Materials"],
        "15121": ["Leather Bags", "Wallets", "Belts"],
        "25931": ["Steel Utensils", "Brass Utensils", "Kitchenware"],
        "32909": ["Handicrafts", "Decorative Items", "Gift Articles"],
        "62011": ["Web Development", "Software Services", "IT Consultancy"],
    }

    def __init__(self, api_url: str | None = None) -> None:
        self.api_url = api_url or UDYAM_API_URL
        self.sample_records = self._load_samples()

    def fetch_by_udyam_number(self, udyam_number: str) -> MSEProfile:
        """Fetch profile by Udyam number using API/samples/mock fallback."""
        normalized = str(udyam_number or "").strip().upper()
        is_valid, error = self.validate_udyam_number(normalized)
        if not is_valid:
            raise ValueError(error)

        for record in self.sample_records:
            if str(record.get("udyam_number", "")).upper() == normalized:
                return MSEProfile(**record)

        api_profile = self._fetch_from_api(normalized)
        if api_profile is not None:
            return api_profile

        return self._generate_mock_profile(normalized)

    def validate_udyam_number(self, udyam_number: str) -> tuple[bool, str]:
        """Validate Udyam format: UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}."""
        if not isinstance(udyam_number, str) or not udyam_number:
            return False, "Udyam number is required."
        if not self.UDYAM_PATTERN.match(udyam_number.strip().upper()):
            return False, "Invalid Udyam format. Expected: UDYAM-XX-00-0000000"
        return True, ""

    def _load_samples(self) -> list[dict[str, Any]]:
        path = Path(__file__).resolve().parents[2] / "data" / "mse_data" / "sample_udyam_records.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _fetch_from_api(self, udyam_number: str) -> MSEProfile | None:
        """Attempt live API fetch when endpoint supports it."""
        if not self.api_url:
            return None
        try:
            response = requests.get(
                self.api_url,
                params={"udyam_number": udyam_number},
                timeout=10,
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            if not isinstance(payload, dict):
                return None
            required = {"udyam_number", "enterprise_name", "owner_name", "nic_2digit"}
            if not required.issubset(payload.keys()):
                return None
            return MSEProfile(**payload)
        except (requests.RequestException, ValueError, TypeError):
            return None

    def _generate_mock_profile(self, udyam_number: str) -> MSEProfile:
        """Generate deterministic mock MSE profile from Udyam number."""
        code_parts = udyam_number.split("-")
        state_code = code_parts[1]
        district_code = int(code_parts[2])
        serial = int(code_parts[3])

        state_name = self.STATE_CODE_TO_NAME.get(state_code, "Rajasthan")
        districts = self.DISTRICT_BY_STATE.get(state_name, ["Jaipur"])
        district = districts[district_code % len(districts)]

        rng = random.Random(serial)
        nic_2digit, nic_5digit, nic_desc, major_activity = rng.choice(self.NIC_OPTIONS)
        products = self.PRODUCT_HINTS.get(nic_5digit, ["General Product"])

        owner_gender = rng.choice(["Male", "Female", "Other"])
        is_women_owned = owner_gender == "Female"
        owner_name = {
            "Male": rng.choice(["Ravi Sharma", "Imran Khan", "Vijay Patel", "Amit Das"]),
            "Female": rng.choice(["Kavita Sharma", "Meenakshi Iyer", "Sutapa Das", "Hetal Patel"]),
            "Other": rng.choice(["Aarav Singh", "Sam Rai"]),
        }[owner_gender]
        enterprise_type = rng.choice(["Micro", "Small"])
        language = rng.choice(["en", "hi", "ta", "mr", "bn", "te", "kn", "gu"])
        investment = round(rng.uniform(2.0, 85.0), 2)
        turnover = round(rng.uniform(12.0, 950.0), 2)

        gst_state = f"{(district_code % 36) + 1:02d}"
        pan_stub = f"ABCDE{serial % 10000:04d}F"
        gstin = f"{gst_state}{pan_stub}1Z{serial % 9}"

        return MSEProfile(
            udyam_number=udyam_number,
            enterprise_name=f"{district} Enterprise {serial % 1000}",
            owner_name=owner_name,
            owner_gender=owner_gender,  # type: ignore[arg-type]
            enterprise_type=enterprise_type,  # type: ignore[arg-type]
            major_activity=major_activity,  # type: ignore[arg-type]
            nic_2digit=nic_2digit,
            nic_5digit=nic_5digit,
            nic_description=nic_desc,
            state=state_name,
            district=district,
            pincode=f"{rng.randint(100000, 999999)}",
            address=f"{district} Industrial Area, {state_name}",
            mobile=f"+9198{serial % 100000000:08d}",
            email=f"owner{serial % 10000}@vyaparsetu.demo",
            date_of_incorporation=f"201{serial % 10}-{(serial % 12) + 1:02d}-{(serial % 27) + 1:02d}",
            date_of_udyam=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            investment_plant=investment,
            turnover=turnover,
            gstin=gstin,
            pan=pan_stub,
            social_category=rng.choice(["General", "OBC", "SC", "ST"]),
            is_women_owned=is_women_owned,
            language_preference=language,
            products_services=products,
        )


def fetch_udyam_record(udyam_number: str) -> dict[str, Any]:
    """Backward-compatible helper returning dict profile data."""
    try:
        profile = UdyamFetcher().fetch_by_udyam_number(udyam_number)
        return profile.model_dump()
    except ValueError:
        return {
            "udyam_number": udyam_number,
            "enterprise_name": "Sample Enterprise",
            "nic_2digit": "10",
            "state": "Rajasthan",
            "district": "Jaipur",
        }
