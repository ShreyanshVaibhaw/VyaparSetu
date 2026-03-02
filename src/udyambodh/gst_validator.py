"""GSTIN validation utilities."""

from __future__ import annotations

import re
from typing import Any


class GSTValidator:
    """Validate GSTIN format and extract state information."""

    GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
    GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    STATE_CODES = {
        "01": "Jammu and Kashmir",
        "02": "Himachal Pradesh",
        "03": "Punjab",
        "04": "Chandigarh",
        "05": "Uttarakhand",
        "06": "Haryana",
        "07": "Delhi",
        "08": "Rajasthan",
        "09": "Uttar Pradesh",
        "10": "Bihar",
        "11": "Sikkim",
        "12": "Arunachal Pradesh",
        "13": "Nagaland",
        "14": "Manipur",
        "15": "Mizoram",
        "16": "Tripura",
        "17": "Meghalaya",
        "18": "Assam",
        "19": "West Bengal",
        "20": "Jharkhand",
        "21": "Odisha",
        "22": "Chhattisgarh",
        "23": "Madhya Pradesh",
        "24": "Gujarat",
        "25": "Dadra and Nagar Haveli and Daman and Diu",
        "26": "Dadra and Nagar Haveli and Daman and Diu",
        "27": "Maharashtra",
        "28": "Andhra Pradesh",
        "29": "Karnataka",
        "30": "Goa",
        "31": "Lakshadweep",
        "32": "Kerala",
        "33": "Tamil Nadu",
        "34": "Puducherry",
        "35": "Andaman and Nicobar Islands",
        "36": "Telangana",
        "37": "Andhra Pradesh",
        "38": "Ladakh",
    }

    def __init__(self) -> None:
        pass

    def _verify_checksum(self, gstin: str) -> bool:
        """Verify GSTIN checksum using the standard base-36 algorithm."""
        normalized = str(gstin or "").strip().upper()
        if len(normalized) != 15:
            return False

        total = 0
        for i, char in enumerate(normalized[:14]):
            try:
                value = self.GSTIN_CHARSET.index(char)
            except ValueError:
                return False
            factor = 2 if i % 2 == 0 else 1
            product = value * factor
            quotient, remainder = divmod(product, 36)
            total += quotient + remainder

        check_index = (36 - (total % 36)) % 36
        expected_check_digit = self.GSTIN_CHARSET[check_index]
        return normalized[14] == expected_check_digit

    def validate(self, gstin: Any) -> dict[str, Any]:
        """Validate GSTIN format and checksum and return parsed fields."""
        if not isinstance(gstin, str):
            return {
                "valid": False,
                "state_code": "",
                "state_name": "",
                "pan": "",
                "business_name": "",
                "error": "GSTIN must be a string",
            }

        normalized = gstin.strip().upper()
        if not self.GSTIN_PATTERN.match(normalized):
            return {
                "valid": False,
                "state_code": "",
                "state_name": "",
                "pan": "",
                "business_name": "",
                "error": "GSTIN format mismatch",
            }

        if not self._verify_checksum(normalized):
            return {
                "valid": False,
                "state_code": "",
                "state_name": "",
                "pan": "",
                "business_name": "",
                "error": "GSTIN checksum mismatch",
            }

        state_code = normalized[:2]
        pan = normalized[2:12]
        return {
            "valid": True,
            "state_code": state_code,
            "state_name": self.extract_state_from_gst(normalized),
            "pan": pan,
            "business_name": f"Demo Business {pan[-4:]}",
            "error": "",
        }

    def validate_gstin(self, gstin: Any) -> dict[str, Any]:
        """Validate GSTIN and return parsed fields in demo-safe format."""
        return self.validate(gstin)

    def extract_state_from_gst(self, gstin: Any) -> str:
        """Extract and map GST state code to state name."""
        if not isinstance(gstin, str):
            return "Unknown"
        normalized = gstin.strip().upper()
        if len(normalized) < 2:
            return "Unknown"
        return self.STATE_CODES.get(normalized[:2], "Unknown")


def validate_gstin(gstin: str) -> bool:
    """Backward-compatible boolean GSTIN validator."""
    return GSTValidator().validate_gstin(gstin)["valid"]
