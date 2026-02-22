"""Configuration constants for the VyaparSetu project.

Defaults are kept identical to the prompt spec while allowing `.env` overrides.
"""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


def _env_str(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value.strip())
    except (TypeError, ValueError):
        return default


PROJECT_NAME = _env_str("PROJECT_NAME", "VyaparSetu")
PROJECT_SANSKRIT = _env_str("PROJECT_SANSKRIT", "व्यापारसेतु")
TAGLINE = _env_str("TAGLINE", "From Udyam to ONDC — AI that onboards India's MSEs")

OLLAMA_MODEL = _env_str("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_HOST = _env_str("OLLAMA_HOST", "localhost")
OLLAMA_PORT = _env_int("OLLAMA_PORT", 11434)
POSTGRES_URI = _env_str("POSTGRES_URI", "postgresql://vyaparsetu:vyaparsetu2026@localhost:5432/vyaparsetu")
QDRANT_HOST = _env_str("QDRANT_HOST", "localhost")
QDRANT_PORT = _env_int("QDRANT_PORT", 6333)
EMBEDDING_MODEL = _env_str("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
BHASHINI_API_URL = _env_str("BHASHINI_API_URL", "https://meity-auth.ulcacontrib.org")
BHASHINI_INFERENCE_URL = _env_str("BHASHINI_INFERENCE_URL", "https://dhruva-api.bhashini.gov.in")
SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "en": "English",
    "ta": "Tamil",
    "mr": "Marathi",
    "bn": "Bengali",
    "te": "Telugu",
    "kn": "Kannada",
    "gu": "Gujarati",
}
UDYAM_API_URL = _env_str("UDYAM_API_URL", "https://udyamregistration.gov.in/api")
GST_API_URL = _env_str("GST_API_URL", "https://gst.gov.in/api")
ONDC_NETWORK_URL = _env_str("ONDC_NETWORK_URL", "https://ondc.org/api")
TEAM_PORTAL_URL = _env_str("TEAM_PORTAL_URL", "https://team.msmemart.com")
MSE_TYPES = ["Micro", "Small"]
BUSINESS_ACTIVITIES = ["Manufacturing", "Services", "Trading"]
TEAM_WOMEN_TARGET = _env_float("TEAM_WOMEN_TARGET", 0.50)
SNP_MATCH_WEIGHTS = {
    "domain": 0.30,
    "geography": 0.20,
    "language": 0.15,
    "cost": 0.15,
    "performance": 0.10,
    "tech_fit": 0.10,
}
ONBOARDING_STAGES = ["Registered", "Catalog_Created", "SNP_Matched", "Live", "First_Order"]
