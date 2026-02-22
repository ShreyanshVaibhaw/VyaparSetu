"""Registration engine for TEAM onboarding workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.common.models import MSEProfile, TEAMRegistration


class RegistrationEngine:
    """Build TEAM registration packages from auto/manual inputs."""

    def __init__(self, udyam_fetcher: Any, gst_validator: Any, business_classifier: Any) -> None:
        self.fetcher = udyam_fetcher
        self.gst = gst_validator
        self.classifier = business_classifier
        self._registrations: dict[str, TEAMRegistration] = {}

    def auto_register(self, udyam_number: str, language: str = "en") -> TEAMRegistration:
        """End-to-end auto registration pipeline."""
        is_valid, error = self.fetcher.validate_udyam_number(udyam_number)
        if not is_valid:
            raise ValueError(error)

        profile = self.fetcher.fetch_by_udyam_number(udyam_number)
        gst_result = (
            self.gst.validate_gstin(profile.gstin)
            if getattr(profile, "gstin", None)
            else {"valid": False}
        )

        classification = self.classifier.classify_hybrid(profile)
        primary = classification.get("primary_l1", "General")
        secondary = classification.get("secondary", [])
        categories = [primary] + [c for c in secondary if c != primary]

        registration = TEAMRegistration(
            registration_id=f"TEAM-{uuid4().hex[:12].upper()}",
            mse_udyam=profile.udyam_number,
            mse_profile=profile,
            product_categories=categories,
            transaction_type="Both",
            preferred_snp_id=None,
            catalog_items=[],
            consent_given=True,
            language=language,
            registration_status="Submitted" if gst_result.get("valid") or profile.gstin is None else "Draft",
            created_at=datetime.now(timezone.utc),
            submitted_at=datetime.now(timezone.utc),
        )
        self._registrations[registration.registration_id] = registration
        return registration

    def manual_register(self, form_data: dict[str, Any]) -> TEAMRegistration:
        """Create registration from manually entered form fields."""
        profile = self._profile_from_form(form_data)
        classification = self.classifier.classify_hybrid(profile)
        categories = [classification.get("primary_l1", "General")]
        categories.extend(classification.get("secondary", []))
        categories = [c for i, c in enumerate(categories) if c and c not in categories[:i]]

        registration = TEAMRegistration(
            registration_id=f"TEAM-{uuid4().hex[:12].upper()}",
            mse_udyam=profile.udyam_number,
            mse_profile=profile,
            product_categories=categories,
            transaction_type=form_data.get("transaction_type", "Both"),
            preferred_snp_id=form_data.get("preferred_snp_id"),
            catalog_items=[],
            consent_given=bool(form_data.get("consent_given", True)),
            language=form_data.get("language", profile.language_preference or "en"),
            registration_status="Draft",
            created_at=datetime.now(timezone.utc),
            submitted_at=None,
        )
        self._registrations[registration.registration_id] = registration
        return registration

    def get_registration_status(self, registration_id: str) -> str:
        """Return status for a registration id."""
        item = self._registrations.get(registration_id)
        return item.registration_status if item else "Not_Found"

    def _profile_from_form(self, form_data: dict[str, Any]) -> MSEProfile:
        defaults = {
            "udyam_number": form_data.get("udyam_number", "UDYAM-RJ-00-0000000"),
            "enterprise_name": form_data.get("enterprise_name", "Manual Enterprise"),
            "owner_name": form_data.get("owner_name", "Owner"),
            "owner_gender": form_data.get("owner_gender", "Male"),
            "enterprise_type": form_data.get("enterprise_type", "Micro"),
            "major_activity": form_data.get("major_activity", "Manufacturing"),
            "nic_2digit": form_data.get("nic_2digit", "10"),
            "nic_5digit": form_data.get("nic_5digit", "10795"),
            "nic_description": form_data.get("nic_description", "Manufacture of food products"),
            "state": form_data.get("state", "Rajasthan"),
            "district": form_data.get("district", "Jaipur"),
            "pincode": form_data.get("pincode", "302001"),
            "address": form_data.get("address", "Manual Address"),
            "mobile": form_data.get("mobile"),
            "email": form_data.get("email"),
            "date_of_incorporation": form_data.get("date_of_incorporation"),
            "date_of_udyam": form_data.get("date_of_udyam"),
            "investment_plant": form_data.get("investment_plant"),
            "turnover": form_data.get("turnover"),
            "gstin": form_data.get("gstin"),
            "pan": form_data.get("pan"),
            "social_category": form_data.get("social_category"),
            "is_women_owned": bool(form_data.get("is_women_owned", False)),
            "language_preference": form_data.get("language_preference", "en"),
            "products_services": form_data.get("products_services", []),
        }
        return MSEProfile(**defaults)


def build_registration_payload(udyam_data: dict[str, Any], gst_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Backward-compatible helper for payload generation."""
    payload = {
        "enterprise_name": udyam_data.get("enterprise_name", ""),
        "udyam_number": udyam_data.get("udyam_number", ""),
        "nic_code": udyam_data.get("nic_2digit", udyam_data.get("nic_code", "")),
        "location": {
            "state": udyam_data.get("state", ""),
            "district": udyam_data.get("district", ""),
        },
    }
    if gst_data:
        payload["gst"] = gst_data
    return payload
