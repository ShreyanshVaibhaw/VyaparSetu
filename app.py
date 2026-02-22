"""VyaparSetu Streamlit dashboard application (Prompt 7)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from config import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_PORT,
    POSTGRES_URI,
    PROJECT_NAME,
    PROJECT_SANSKRIT,
    SNP_MATCH_WEIGHTS,
    SUPPORTED_LANGUAGES,
    TAGLINE,
)
from src.common.logger import audit_event, get_logger
from src.common.models import MSEProfile, ONDCCatalogItem, ProductGenerationRequest
from src.common.submission_pack import generate_submission_pack
from src.llm.ollama_client import LLMClient
from src.reporting.admin_report import export_admin_excel, generate_admin_pdf
from src.reporting.catalog_export import (
    export_catalog_csv,
    export_catalog_ondc_json,
    export_catalog_pdf,
)
from src.reporting.registration_report import generate_registration_pdf
from src.sahayakmap.matching_engine import SNPMatchingEngine
from src.sahayakmap.scoring import SNPScorer
from src.sahayakmap.snp_profiler import SNPProfiler
from src.udyambodh.business_classifier import BusinessClassifier
from src.udyambodh.gst_validator import GSTValidator
from src.udyambodh.ocr_engine import UdyamOCR
from src.udyambodh.registration_engine import RegistrationEngine
from src.udyambodh.udyam_fetcher import UdyamFetcher
from src.vastrasuchi.catalog_generator import CatalogGenerator
from src.vastrasuchi.hsn_mapper import HSNMapper
from src.vastrasuchi.image_processor import ImageProcessor
from src.vastrasuchi.ondc_formatter import ONDCFormatter
from src.vastrasuchi.pricing_engine import PricingEngine
from src.vastrasuchi.product_classifier import ProductClassifier
from src.voice.bhashini_client import BhashiniClient
from src.vriddhidisha.catalog_performance import CatalogPerformance
from src.vriddhidisha.dashboard_data import DashboardDataPrep
from src.vriddhidisha.funnel_analytics import FunnelAnalytics
from src.vriddhidisha.geo_analytics import GeoAnalytics
from src.vriddhidisha.women_mse_tracker import WomenMSETracker

try:
    from streamlit_folium import st_folium
except Exception:
    st_folium = None


logger = get_logger(__name__)


PAGE_KEYS = [
    "home",
    "register",
    "admin",
    "prakriti",
    "competition",
    "about",
]
PAGE_LABELS = {
    "en": {
        "home": "Home",
        "register": "Register & Onboard",
        "admin": "Admin Dashboard",
        "prakriti": "Prakriti Assessment",
        "competition": "Competition Readiness",
        "about": "About",
    },
    "hi": {
        "home": "होम",
        "register": "पंजीकरण और ऑनबोर्डिंग",
        "admin": "एडमिन डैशबोर्ड",
        "prakriti": "प्रकृति असेसमेंट",
        "competition": "प्रतियोगिता तैयारी",
        "about": "परिचय",
    },
}
DEMO_PRODUCTS = [
    "aam ka achaar, ghar ka bana hua, 500 gram, desi ghee mein",
    "Pure silk Kanchipuram saree, 6.5 meter, with zari border",
    "Brass decorative flower vase, 12 inch, hand-engraved",
    "Organic turmeric powder, 200g pack",
    "Genuine leather laptop bag, 15 inch",
]


def _nav_lang() -> str:
    return "hi" if st.session_state.get("language") == "hi" else "en"


def _page_label(page_key: str, lang: str | None = None) -> str:
    current_lang = lang or _nav_lang()
    labels = PAGE_LABELS.get(current_lang, PAGE_LABELS["en"])
    return labels.get(page_key, page_key)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except (TypeError, ValueError):
        return default


ADMIN_MAX_FAILED_ATTEMPTS = max(1, _env_int("VYAPARSETU_ADMIN_MAX_FAILED_ATTEMPTS", 5))
ADMIN_LOCKOUT_SECONDS = max(30, _env_int("VYAPARSETU_ADMIN_LOCKOUT_SECONDS", 300))
ACTION_COOLDOWN_SECONDS = max(0.2, _env_float("VYAPARSETU_ACTION_COOLDOWN_SECONDS", 1.5))


def root() -> Path:
    return Path(__file__).resolve().parent


def data_path(*parts: str) -> Path:
    return root().joinpath("data", *parts)


def ensure_synthetic_data() -> None:
    required = [
        data_path("synthetic", "mse_profiles.csv"),
        data_path("synthetic", "products.csv"),
        data_path("synthetic", "onboarding_funnel.csv"),
    ]
    if all(path.exists() for path in required):
        return
    script = root() / "scripts" / "generate_synthetic_data.py"
    try:
        subprocess.run([sys.executable, str(script)], check=True)
    except Exception as exc:
        logger.warning("Synthetic data generation failed, continuing with available datasets: %s", exc)
        audit_event("synthetic_data_generate", status="error", error=str(exc))


@st.cache_resource
def llm_client() -> LLMClient:
    return LLMClient(host=OLLAMA_HOST, port=OLLAMA_PORT, model=OLLAMA_MODEL)


@st.cache_resource
def udyambodh_stack() -> dict[str, Any]:
    llm = llm_client()
    fetcher = UdyamFetcher()
    gst = GSTValidator()
    classifier = BusinessClassifier(
        llm_client=llm,
        nic_to_ondc_path=str(data_path("ondc_taxonomy", "nic_to_ondc.json")),
        categories_path=str(data_path("ondc_taxonomy", "categories.json")),
    )
    return {
        "fetcher": fetcher,
        "gst": gst,
        "ocr": UdyamOCR(),
        "bhashini": BhashiniClient(),
        "classifier": classifier,
        "registration": RegistrationEngine(fetcher, gst, classifier),
    }


@st.cache_resource
def vastrasuchi_stack() -> dict[str, Any]:
    llm = llm_client()
    classifier = ProductClassifier(
        categories_path=str(data_path("ondc_taxonomy", "categories.json")),
        hsn_mapping_path=str(data_path("ondc_taxonomy", "hsn_mapping.json")),
        llm_client=llm,
    )
    hsn = HSNMapper(str(data_path("ondc_taxonomy", "hsn_mapping.json")))
    pricing = PricingEngine()
    return {
        "generator": CatalogGenerator(llm, classifier, hsn, pricing),
        "formatter": ONDCFormatter(str(data_path("catalog_templates", "attribute_schemas.json"))),
        "image": ImageProcessor(),
    }


@st.cache_resource
def sahayakmap_stack() -> dict[str, Any]:
    profiler = SNPProfiler(
        snp_database_path=str(data_path("snp_profiles", "snp_database.json")),
        snp_performance_path=str(data_path("snp_profiles", "snp_performance.json")),
    )
    engine = SNPMatchingEngine(profiler, SNPScorer(SNP_MATCH_WEIGHTS), llm_client())
    return {"profiler": profiler, "engine": engine}


@st.cache_resource
def vriddhidisha_stack() -> dict[str, Any]:
    ensure_synthetic_data()
    funnel = FunnelAnalytics(str(data_path("synthetic", "onboarding_funnel.csv")))
    geo = GeoAnalytics(str(data_path("synthetic", "mse_profiles.csv")), str(data_path("mse_data", "state_districts.json")))
    women = WomenMSETracker(str(data_path("synthetic", "mse_profiles.csv")))
    catalog = CatalogPerformance()
    prep = DashboardDataPrep(funnel=funnel, geo=geo, women=women, catalog=catalog)
    return {"funnel": funnel, "geo": geo, "women": women, "catalog": catalog, "prep": prep}


@st.cache_data
def sample_mses() -> list[dict[str, Any]]:
    try:
        data = json.loads(data_path("mse_data", "sample_udyam_records.json").read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data
def home_metrics() -> dict[str, int]:
    ensure_synthetic_data()
    out = {"mse": 0, "products": 0, "snps": 0, "states": 0}
    try:
        mse = pd.read_csv(data_path("synthetic", "mse_profiles.csv"))
        out["mse"] = len(mse)
        out["states"] = int(mse["state"].nunique())
    except Exception as exc:
        logger.warning("Failed to load synthetic MSE metrics: %s", exc)
    try:
        out["products"] = len(pd.read_csv(data_path("synthetic", "products.csv")))
    except Exception as exc:
        logger.warning("Failed to load synthetic product metrics: %s", exc)
    try:
        snps = json.loads(data_path("snp_profiles", "snp_database.json").read_text(encoding="utf-8"))
        if isinstance(snps, list):
            out["snps"] = len(snps)
    except Exception as exc:
        logger.warning("Failed to load SNP metrics: %s", exc)
    return out


def init_state() -> None:
    defaults = {
        "mse_profile": None,
        "classification": None,
        "catalog_items": [],
        "snp_matches": [],
        "selected_snp": None,
        "onboarding_step": 1,
        "language": "hi",
        "registered_package": None,
        "admin_ok": False,
        "quick_items": [],
        "last_registration_seconds": None,
        "last_catalog_seconds": None,
        "last_match_seconds": None,
        "last_action_ts": {},
        "admin_fail_count": 0,
        "admin_lock_until": 0.0,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def reset_flow() -> None:
    for key in ["mse_profile", "classification", "catalog_items", "snp_matches", "selected_snp", "registered_package"]:
        st.session_state[key] = None if key in {"mse_profile", "classification", "selected_snp", "registered_package"} else []
    st.session_state["onboarding_step"] = 1
    st.session_state["last_registration_seconds"] = None
    st.session_state["last_catalog_seconds"] = None
    st.session_state["last_match_seconds"] = None
    st.session_state["last_action_ts"] = {}


def _mask_identifier(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    text = str(value)
    if len(text) <= keep:
        return "*" * len(text)
    return ("*" * (len(text) - keep)) + text[-keep:]


def _password_sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _expected_admin_hash() -> str:
    configured_hash = os.getenv("VYAPARSETU_ADMIN_PASSWORD_HASH", "").strip().lower()
    if configured_hash:
        return configured_hash
    configured_plain = os.getenv("VYAPARSETU_ADMIN_PASSWORD", "team2026")
    return _password_sha256(configured_plain)


def _using_default_admin_secret() -> bool:
    if os.getenv("VYAPARSETU_ADMIN_PASSWORD_HASH", "").strip():
        return False
    return os.getenv("VYAPARSETU_ADMIN_PASSWORD", "team2026") == "team2026"


def _admin_lock_remaining_seconds() -> int:
    lock_until = float(st.session_state.get("admin_lock_until", 0.0) or 0.0)
    now = time.time()
    if lock_until <= now:
        return 0
    return int(lock_until - now)


def _throttle_action(action_key: str, cooldown_seconds: float = ACTION_COOLDOWN_SECONDS) -> tuple[bool, float]:
    last_action_ts = st.session_state.setdefault("last_action_ts", {})
    now = time.time()
    last = float(last_action_ts.get(action_key, 0.0) or 0.0)
    elapsed = now - last
    if elapsed < cooldown_seconds:
        return False, round(cooldown_seconds - elapsed, 2)
    last_action_ts[action_key] = now
    return True, 0.0


def _runtime_mode(ollama_up: bool, postgres_up: bool) -> str:
    if ollama_up and postgres_up:
        return "FULL"
    if ollama_up:
        return "PARTIAL"
    return "DEMO"


def _fmt_timing(value: float | None) -> str:
    return f"{value:.1f}s" if isinstance(value, (int, float)) else "-"


def _record_timing(metric_key: str, elapsed: float) -> None:
    st.session_state[metric_key] = round(float(elapsed), 3)
    logger.info("%s completed in %.3fs", metric_key, elapsed)


def _score_color(score: float) -> str:
    if score > 0.8:
        return "#138808"
    if score >= 0.5:
        return "#CA8A04"
    return "#EA580C"


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind:wght@400;600;700&family=Space+Grotesk:wght@400;600;700&display=swap');
        :root {
            --vs-navy: #0b1f44;
            --vs-saffron: #f59e0b;
            --vs-green: #138808;
            --vs-muted: #51607a;
            --vs-card: #ffffff;
            --vs-border: #dde6f5;
        }
        html, body, [class*="css"] {
            font-family: 'Hind', sans-serif;
            background: radial-gradient(circle at 8% 10%, #fff7ea 0%, #f7fafc 45%, #edf4ff 100%);
            color: var(--vs-navy);
        }
        h1,h2,h3,h4 {
            font-family: 'Space Grotesk', sans-serif;
            color: var(--vs-navy);
            letter-spacing: 0.2px;
        }
        .stAppHeader {
            background: linear-gradient(90deg, rgba(255,255,255,0.6), rgba(255,255,255,0.2));
        }
        .card {
            background: var(--vs-card);
            border: 1px solid var(--vs-border);
            border-left: 6px solid var(--vs-saffron);
            border-radius: 14px;
            padding: 14px;
            box-shadow: 0 8px 24px rgba(11, 31, 68, 0.08);
            margin-bottom: 10px;
        }
        .voice-card {
            background: linear-gradient(135deg, #fff8ee 0%, #ffffff 60%, #eaf7ff 100%);
            border: 1px solid #f2dfc3;
            border-left: 6px solid #fb923c;
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 12px;
        }
        .chip {
            display:inline-block;
            border-radius:999px;
            padding:2px 10px;
            background:#eef6ff;
            border:1px solid #d8e8ff;
            margin:3px;
        }
        .subtle {
            color: var(--vs-muted);
            font-size: 0.95rem;
        }
        [data-testid="stSidebar"] {
            border-right: 1px solid #e4eaf6;
            background: linear-gradient(180deg, #fefefe 0%, #f5f9ff 100%);
        }
        .stButton > button {
            border-radius: 10px;
            border: 1px solid #cfdcf0;
        }
        .stDownloadButton > button {
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def system_status() -> tuple[bool, bool]:
    try:
        ollama = llm_client().health_check()
    except Exception as exc:
        logger.info("Ollama health check unavailable: %s", exc)
        ollama = False
    try:
        from sqlalchemy import create_engine

        engine = create_engine(POSTGRES_URI, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        postgres = True
    except Exception as exc:
        logger.info("PostgreSQL health check unavailable: %s", exc)
        postgres = False
    return ollama, postgres


def sidebar() -> str:
    with st.sidebar:
        st.markdown("### 🏪 VyaparSetu")
        st.markdown(f"**{PROJECT_SANSKRIT}**")
        st.caption("ONDC onboarding suite")
        st.markdown("---")

        lang_options = list(SUPPORTED_LANGUAGES.keys())
        current_lang = st.session_state.get("language", lang_options[0] if lang_options else "en")
        if current_lang not in lang_options and lang_options:
            current_lang = lang_options[0]

        nav_lang = _nav_lang()
        lang_label = "भाषा" if nav_lang == "hi" else "Language"
        lang = st.selectbox(
            lang_label,
            lang_options,
            index=lang_options.index(current_lang) if lang_options else 0,
            format_func=lambda x: f"{SUPPORTED_LANGUAGES[x]} ({x})",
        )
        st.session_state["language"] = lang
        nav_lang = _nav_lang()

        st.caption("नेविगेशन" if nav_lang == "hi" else "Navigation")
        page = st.radio(
            "Page",
            PAGE_KEYS,
            format_func=lambda key: _page_label(key, nav_lang),
            label_visibility="collapsed",
        )

        ollama, postgres = system_status()
        dot_g = "<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:#138808;margin-right:8px;'></span>"
        dot_r = "<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:#C2410C;margin-right:8px;'></span>"
        st.markdown("#### System Status")
        st.markdown(f"{dot_g if ollama else dot_r} Ollama", unsafe_allow_html=True)
        st.markdown(f"{dot_g if postgres else dot_r} PostgreSQL", unsafe_allow_html=True)
        mode = _runtime_mode(bool(ollama), bool(postgres))
        mode_color = "#138808" if mode == "FULL" else "#CA8A04" if mode == "PARTIAL" else "#EA580C"
        st.markdown(f"**Runtime Mode:** <span style='color:{mode_color}'>{mode}</span>", unsafe_allow_html=True)

        st.caption(
            "Last registration: "
            f"{_fmt_timing(st.session_state.get('last_registration_seconds'))} | "
            "Last catalog: "
            f"{_fmt_timing(st.session_state.get('last_catalog_seconds'))} | "
            "Last match: "
            f"{_fmt_timing(st.session_state.get('last_match_seconds'))}"
        )

        if st.button("Start Over", use_container_width=True):
            reset_flow()
            st.toast("Workflow reset", icon="🔄")

        st.caption("Version: v0.7.0")
        if _using_default_admin_secret():
            st.caption("Security: default admin password active; set env secret.")

    if not ollama:
        st.warning("Running in demo mode with cached AI responses")
    return page


def step_tracker(step: int) -> None:
    chips = []
    for i in range(1, 6):
        color = "#138808" if i == step else "#fff7eb"
        text = "white" if i == step else "#000080"
        chips.append(
            f"<span style='display:inline-block;padding:3px 12px;border-radius:999px;border:1px solid #f2d7b1;background:{color};color:{text};margin-right:6px'>{i}</span>"
        )
    st.markdown("".join(chips), unsafe_allow_html=True)


def save_upload(uploaded_file: Any) -> str:
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


def _audio_input_widget(label: str, key: str) -> Any:
    if hasattr(st, "audio_input"):
        return st.audio_input(label, key=key)
    return st.file_uploader(f"{label} (Upload audio file)", type=["wav", "mp3", "m4a"], key=f"{key}_file")


def _audio_bytes(audio_obj: Any) -> bytes:
    if audio_obj is None:
        return b""
    if hasattr(audio_obj, "getvalue"):
        data = audio_obj.getvalue()
        return data if isinstance(data, (bytes, bytearray)) else b""
    if isinstance(audio_obj, (bytes, bytearray)):
        return bytes(audio_obj)
    return b""


def _extract_udyam_from_text(text: str) -> str | None:
    match = re.search(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", text.upper())
    return match.group(0) if match else None


def _voice_product_hint(text: str, udyam: str | None = None) -> str:
    cleaned = text.strip()
    if udyam:
        cleaned = cleaned.replace(udyam, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    return cleaned


def _transcribe_audio(audio_obj: Any, language: str, bhashini: BhashiniClient) -> str:
    data = _audio_bytes(audio_obj)
    if not data:
        return ""
    try:
        result = bhashini.transcribe(data, language)
    except Exception as exc:
        logger.warning("Voice transcription failed for language '%s': %s", language, exc)
        audit_event("voice_transcription", status="error", language=language, error=str(exc))
        return ""
    return str(getattr(result, "text", "") or "").strip()


def render_profile(profile: MSEProfile) -> None:
    women = "🟣 Women-owned" if profile.is_women_owned else "Standard ownership"
    st.markdown(
        f"""
        <div class='card'>
          <h4 style='margin:0'>{profile.enterprise_name}</h4>
          <div>
            <span class='chip'>{profile.enterprise_type}</span>
            <span class='chip'>{profile.major_activity}</span>
            <span class='chip'>{profile.state}, {profile.district}</span>
            <span class='chip'>{women}</span>
          </div>
          <p><b>Owner:</b> {profile.owner_name} ({profile.owner_gender})</p>
          <p><b>NIC:</b> {profile.nic_2digit}/{profile.nic_5digit} - {profile.nic_description}</p>
          <p><b>Turnover:</b> {profile.turnover or 0} lakh | <b>Investment:</b> {profile.investment_plant or 0} lakh</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _temp_file_path(suffix: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        return tmp.name


def _safe_unlink(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to remove temporary file '%s': %s", path, exc)


def _read_and_cleanup(path: str) -> bytes:
    file_path = Path(path)
    try:
        return file_path.read_bytes()
    finally:
        _safe_unlink(file_path)


def registration_pdf_bytes(registration: Any) -> bytes:
    path = _temp_file_path(".pdf")
    generate_registration_pdf(registration, path)
    return _read_and_cleanup(path)


def catalog_pdf_bytes(items: list[ONDCCatalogItem], mse: MSEProfile) -> bytes:
    path = _temp_file_path(".pdf")
    export_catalog_pdf(items, mse, path)
    return _read_and_cleanup(path)


def catalog_csv_bytes(items: list[ONDCCatalogItem]) -> bytes:
    path = _temp_file_path(".csv")
    export_catalog_csv(items, path)
    return _read_and_cleanup(path)


def catalog_ondc_json_bytes(items: list[ONDCCatalogItem]) -> bytes:
    path = _temp_file_path(".json")
    export_catalog_ondc_json(items, path)
    return _read_and_cleanup(path)


def admin_pdf_bytes(analytics_data: dict[str, Any]) -> bytes:
    path = _temp_file_path(".pdf")
    generate_admin_pdf(analytics_data, path)
    return _read_and_cleanup(path)


def admin_excel_bytes(analytics_data: dict[str, Any]) -> bytes:
    path = _temp_file_path(".xlsx")
    export_admin_excel(analytics_data, path)
    return _read_and_cleanup(path)


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        logger.warning("Failed to parse JSON file '%s': %s", path, exc)
        return {}


def _read_submission_outputs() -> dict[str, Any]:
    base = root() / "outputs" / "submission"
    return {
        "score": _load_json_if_exists(base / "readiness_score.json"),
        "security": _load_json_if_exists(base / "security_snapshot.json"),
        "reference": _load_json_if_exists(base / "reference_validation.json"),
        "runtime": _load_json_if_exists(base / "runtime_snapshot.json"),
        "demo": _load_json_if_exists(base / "demo_summary.json"),
        "overview_path": str(base / "submission_overview.md"),
        "zip_path": str(base / "vyaparsetu_submission_pack.zip"),
    }


def render_map(map_obj: Any, key: str) -> None:
    if st_folium:
        st_folium(map_obj, width=None, height=420, key=key)
    else:
        st.components.v1.html(map_obj._repr_html_(), height=420, scrolling=False)


def item_to_demo_mse(item: ONDCCatalogItem, enterprise_name: str) -> MSEProfile:
    """Build minimal synthetic MSE profile for quick catalog PDF export."""
    return MSEProfile(
        udyam_number=item.mse_udyam,
        enterprise_name=enterprise_name,
        owner_name="Owner",
        owner_gender="Male",
        enterprise_type="Micro",
        major_activity="Manufacturing",
        nic_2digit="10",
        nic_5digit="10795",
        nic_description="Manufacture of papads and similar foods",
        state="Rajasthan",
        district="Jaipur",
        pincode="302001",
        address="Jaipur",
        mobile=None,
        email=None,
        date_of_incorporation=None,
        date_of_udyam=None,
        investment_plant=5.0,
        turnover=20.0,
        gstin=None,
        pan=None,
        social_category=None,
        is_women_owned=False,
        language_preference="en",
        products_services=[item.product_name_en],
    )


def page_home() -> None:
    m = home_metrics()
    st.markdown(
        f"""
        <div class='card' style='background:linear-gradient(135deg,#fff4df 0%,#fff 50%,#eaf7ef 100%);'>
          <h1 style='margin-bottom:4px'>VyaparSetu - From Udyam to ONDC</h1>
          <p style='margin:0'>{TAGLINE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    modules = [
        ("📋 UdyamBodh", "Smart Registration - enter Udyam, we do the rest"),
        ("🛍️ VastraSuchi", "AI Catalog - photos to product listings"),
        ("🤝 SahayakMap", "SNP Matching - find your perfect e-commerce partner"),
        ("📊 VriddhiDisha", "Growth Dashboard - track your ONDC journey"),
    ]
    cols = st.columns(4)
    for col, (t, d) in zip(cols, modules):
        with col:
            st.markdown(f"<div class='card'><h4 style='margin:0'>{t}</h4><p style='margin:0'>{d}</p></div>", unsafe_allow_html=True)

    st.markdown("### Quick Stats")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MSEs Onboarded", f"{m['mse']:,}")
    c2.metric("Products Listed", f"{m['products']:,}")
    c3.metric("SNPs Available", f"{m['snps']:,}")
    c4.metric("States Covered", f"{m['states']:,}")

    st.markdown("<div class='card' style='border-left-color:#138808;'><h3 style='margin:0'>Helping India's 63 million MSMEs go digital</h3></div>", unsafe_allow_html=True)


def fetch_profile(udyam_num: str, cert_file: Any, demo: str, stack: dict[str, Any]) -> tuple[MSEProfile | None, str]:
    fetcher: UdyamFetcher = stack["fetcher"]
    ocr: UdyamOCR = stack["ocr"]
    demos = sample_mses()

    if udyam_num.strip():
        return fetcher.fetch_by_udyam_number(udyam_num.strip().upper()), "Fetched via Udyam number"

    if cert_file is not None:
        cert_path = save_upload(cert_file)
        try:
            info = ocr.extract_from_certificate(cert_path)
        finally:
            _safe_unlink(cert_path)
        if info.get("udyam_number"):
            return fetcher.fetch_by_udyam_number(str(info["udyam_number"])), "Fetched via OCR + Udyam"
        return None, "OCR could not extract a valid Udyam number"

    if demo and demo != "Select demo MSE":
        selected = demo.split(" | ")[0]
        for row in demos:
            if row.get("udyam_number") == selected:
                return MSEProfile(**row), "Demo MSE loaded"

    return None, "Please provide Udyam number, certificate, or demo MSE"


def page_register() -> None:
    u = udyambodh_stack()
    v = vastrasuchi_stack()
    s = sahayakmap_stack()

    st.markdown("## Register & Onboard")
    st.markdown("<p class='subtle'>Professional guided onboarding with voice-first automation for MSMEs.</p>", unsafe_allow_html=True)
    step_tracker(st.session_state["onboarding_step"])

    st.markdown(
        """
        <div class='card' style='border-left-color:#2563eb;'>
          <b>Quick Guide:</b> 1) Capture business profile 2) Generate ONDC catalog 3) Match best SNP 4) Submit package.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Step 1: Enter Udyam Number")
    c1, c2 = st.columns([2, 1])
    with c1:
        udyam = st.text_input("Enter your Udyam Registration Number", placeholder="UDYAM-XX-00-0000000", help="Format hint: UDYAM-XX-00-0000000")
        cert = st.file_uploader("Upload Udyam Certificate", type=["png", "jpg", "jpeg", "webp"])
        demos = sample_mses()
        demo_pick = st.selectbox("Use Demo MSE", ["Select demo MSE"] + [f"{d['udyam_number']} | {d['enterprise_name']}" for d in demos[:20]])
    with c2:
        st.info(f"Language: {SUPPORTED_LANGUAGES.get(st.session_state['language'], 'English')}")
        voice_onboard_audio = _audio_input_widget("Voice Onboarding (Speak Udyam + products)", key="voice_onboard_audio")

    if st.button("Fetch Details", type="primary", use_container_width=True):
        ok, wait_seconds = _throttle_action("fetch_details")
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before retrying.")
            return
        with st.spinner("📋 UdyamBodh is fetching your details..."):
            try:
                profile, msg = fetch_profile(udyam, cert, demo_pick, u)
                if profile is None:
                    st.error(msg)
                    audit_event("onboarding_fetch_profile", status="failed", reason=msg)
                else:
                    st.session_state["mse_profile"] = profile
                    st.session_state["onboarding_step"] = max(st.session_state["onboarding_step"], 2)
                    st.toast(msg, icon="✅")
                    audit_event(
                        "onboarding_fetch_profile",
                        status="success",
                        source=msg,
                        udyam_masked=_mask_identifier(profile.udyam_number),
                    )
            except Exception as exc:
                audit_event("onboarding_fetch_profile", status="error", error=str(exc))
                st.error(f"Fetch failed: {exc}")

    if st.button("Auto-Onboard from Voice", use_container_width=True):
        ok, wait_seconds = _throttle_action("auto_voice_onboard", cooldown_seconds=2.0)
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before retrying.")
            return
        transcript = _transcribe_audio(voice_onboard_audio, st.session_state["language"], u["bhashini"])
        if not transcript:
            st.error("No voice input detected. Please record and retry.")
            return

        with st.spinner("Processing your voice and preparing onboarding..."):
            try:
                detected_udyam = _extract_udyam_from_text(transcript)
                if not detected_udyam and udyam.strip():
                    detected_udyam = udyam.strip().upper()
                if not detected_udyam and demo_pick and demo_pick != "Select demo MSE":
                    detected_udyam = demo_pick.split(" | ")[0]
                if not detected_udyam and getattr(u["bhashini"], "demo_mode", False):
                    demos = sample_mses()
                    if demos:
                        detected_udyam = str(demos[0].get("udyam_number", "")).strip().upper()
                if not detected_udyam:
                    st.error("Could not detect Udyam number from voice. Please speak it clearly.")
                    audit_event("voice_auto_onboard", status="failed", reason="udyam_not_detected")
                    return

                profile = u["fetcher"].fetch_by_udyam_number(detected_udyam)
                st.session_state["mse_profile"] = profile
                st.session_state["classification"] = u["classifier"].classify_hybrid(profile)
                st.session_state["onboarding_step"] = 3

                product_text = _voice_product_hint(transcript, detected_udyam) or DEMO_PRODUCTS[0]
                if product_text:
                    req = ProductGenerationRequest(
                        mse_udyam=profile.udyam_number,
                        product_description_raw=product_text,
                        product_images=[],
                        language=st.session_state["language"],
                        category_hint=st.session_state["classification"]["primary_l1"],
                    )
                    item = v["generator"].generate_catalog_item(req, profile)
                    st.session_state["catalog_items"] = [item]
                    st.session_state["onboarding_step"] = 4

                    matches = s["engine"].match(
                        profile,
                        [item.category_l1],
                        tech_comfort="medium",
                        transaction_type="B2C",
                        top_k=3,
                    )
                    st.session_state["snp_matches"] = matches
                    if matches:
                        st.session_state["selected_snp"] = matches[0].snp_id
                        st.session_state["onboarding_step"] = 5

                st.success("Voice onboarding complete. Review details below.")
                st.caption(f"Transcript: {transcript}")
                audit_event(
                    "voice_auto_onboard",
                    status="success",
                    udyam_masked=_mask_identifier(profile.udyam_number),
                    auto_catalog=bool(st.session_state.get("catalog_items")),
                    auto_matches=len(st.session_state.get("snp_matches", [])),
                )
            except Exception as exc:
                audit_event("voice_auto_onboard", status="error", error=str(exc))
                st.error(f"Voice auto-onboarding failed: {exc}")

    profile: MSEProfile | None = st.session_state["mse_profile"]
    if not profile:
        st.info("Enter a Udyam number, upload certificate, or choose a demo MSE to continue.")
        return

    st.markdown("### Step 2: Verify Business Details")
    render_profile(profile)

    with st.expander("Edit Details"):
        ec1, ec2 = st.columns(2)
        with ec1:
            ent = st.text_input("Enterprise Name", value=profile.enterprise_name)
            own = st.text_input("Owner", value=profile.owner_name)
        with ec2:
            state = st.text_input("State", value=profile.state)
            district = st.text_input("District", value=profile.district)
        if st.button("Apply Edits"):
            st.session_state["mse_profile"] = profile.model_copy(update={"enterprise_name": ent, "owner_name": own, "state": state, "district": district})
            profile = st.session_state["mse_profile"]
            st.toast("Profile updated", icon="🛠️")

    if st.session_state["classification"] is None:
        try:
            with st.spinner("Classifying business..."):
                st.session_state["classification"] = u["classifier"].classify_hybrid(profile)
        except Exception:
            st.session_state["classification"] = {"primary_l1": "General", "primary_l2": "General", "secondary": [], "confidence": 0.5}

    cls = st.session_state["classification"]
    st.markdown(f"**AI-classified category:** {cls['primary_l1']} > {cls['primary_l2']} | Confidence `{float(cls['confidence'])*100:.1f}%`")

    if st.button("Confirm & Continue", type="primary"):
        st.session_state["onboarding_step"] = max(st.session_state["onboarding_step"], 3)

    if st.session_state["onboarding_step"] < 3:
        return

    st.markdown("### Step 3: Create Product Catalog")
    t1, t2, t3, t4 = st.tabs(["Describe in words", "Upload photos", "Speak", "Use Demo Product"])
    with t1:
        raw = st.text_area("Describe product", key="raw_desc")
    with t2:
        imgs = st.file_uploader("Upload photos (up to 5)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    with t3:
        st.markdown("<div class='voice-card'><b>Voice Input</b><br/>Speak naturally in your language. We will transcribe and generate catalog details.</div>", unsafe_allow_html=True)
        mic_audio = _audio_input_widget("Record product details", key="catalog_mic_audio")
        uploaded_audio = st.file_uploader(
            "Or upload audio file",
            type=["wav", "mp3", "m4a"],
            help="Use this if microphone is unavailable.",
            key="catalog_uploaded_audio",
        )
    with t4:
        demo_prod = st.selectbox("Demo Product", [""] + DEMO_PRODUCTS)

    if st.button("Generate Catalog Entry", type="primary", use_container_width=True):
        ok, wait_seconds = _throttle_action("generate_catalog")
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before generating again.")
            return
        t0 = time.perf_counter()
        try:
            voice_source = mic_audio if mic_audio is not None else uploaded_audio
            voice_text = _transcribe_audio(voice_source, st.session_state["language"], u["bhashini"])

            text = raw.strip() or voice_text.strip() or demo_prod.strip()
            if not text:
                st.error("Provide text/audio/demo product input")
            else:
                image_paths: list[str] = []
                for file in (imgs or [])[:5]:
                    upload_path = ""
                    try:
                        upload_path = save_upload(file)
                        validation = v["image"].validate_image(upload_path)
                        if validation.get("valid"):
                            image_paths.append(v["image"].process_product_image(upload_path))
                        else:
                            logger.info(
                                "Skipped invalid image '%s': %s",
                                getattr(file, "name", "upload"),
                                ", ".join(validation.get("issues", [])),
                            )
                    except Exception as exc:
                        logger.warning("Image processing failed for '%s': %s", getattr(file, "name", "upload"), exc)
                    finally:
                        if upload_path:
                            _safe_unlink(upload_path)

                req = ProductGenerationRequest(
                    mse_udyam=profile.udyam_number,
                    product_description_raw=text,
                    product_images=image_paths,
                    language=st.session_state["language"],
                    category_hint=cls["primary_l1"],
                )
                with st.spinner("🛍️ VastraSuchi is building your catalog..."):
                    item = v["generator"].generate_catalog_item(req, profile)
                st.session_state["catalog_items"].append(item)
                st.toast("Catalog item generated", icon="🛍️")
                audit_event(
                    "catalog_generate",
                    status="success",
                    udyam_masked=_mask_identifier(profile.udyam_number),
                    category_l1=item.category_l1,
                    hsn_code=item.hsn_code,
                )
                _record_timing("last_catalog_seconds", time.perf_counter() - t0)
        except Exception as exc:
            audit_event("catalog_generate", status="error", error=str(exc))
            st.error(f"Catalog generation failed: {exc}")

    items: list[ONDCCatalogItem] = st.session_state["catalog_items"]
    st.markdown(f"**Running total:** {len(items)} products in your catalog")
    if items:
        q = CatalogPerformance().get_catalog_quality_score(items)
        badge = "Excellent" if q["score"] >= 80 else "Good" if q["score"] >= 60 else "Needs Improvement"
        st.markdown(f"Quality score badge: **{badge}** ({q['score']:.1f}/100)")
    else:
        st.info("No catalog items yet. Generate your first ONDC listing above.")

    for i, item in enumerate(items):
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if item.images:
                    try:
                        st.image(item.images[0], use_container_width=True)
                    except Exception:
                        st.caption("Image preview unavailable")
            with c2:
                st.subheader(item.product_name_en)
                st.write(item.short_description)
                st.caption(f"ONDC Breadcrumb: {item.category_l1} > {item.category_l2} > {item.category_l3 or '-'}")
                st.caption(f"HSN {item.hsn_code} | INR {item.price_selling:.2f}")
                st.dataframe(pd.DataFrame([item.attributes]).T.rename(columns={0: "Value"}), use_container_width=True)

            b1, b2, b3 = st.columns(3)
            fb = b1.text_input("feedback", key=f"fb_{i}", label_visibility="collapsed", placeholder="Edit guidance")
            if b1.button("Edit", key=f"edit_{i}") and fb.strip():
                st.session_state["catalog_items"][i] = v["generator"].regenerate_description(item, fb)
                st.toast("Description updated", icon="✍️")
            if b2.button("Approve", key=f"ap_{i}"):
                st.session_state["catalog_items"][i] = item.model_copy(update={"reviewed_by_mse": True})
                st.toast("Approved", icon="✅")
            if b3.button("Regenerate", key=f"rg_{i}"):
                req = ProductGenerationRequest(
                    mse_udyam=profile.udyam_number,
                    product_description_raw=item.short_description,
                    product_images=item.images,
                    language=st.session_state["language"],
                    category_hint=item.category_l1,
                )
                st.session_state["catalog_items"][i] = v["generator"].generate_catalog_item(req, profile)
                st.toast("Regenerated", icon="🔁")

    if items and st.button("Continue to SNP Matching", type="primary"):
        st.session_state["onboarding_step"] = max(st.session_state["onboarding_step"], 4)

    if st.session_state["onboarding_step"] < 4:
        return

    st.markdown("### Step 4: SNP Matching")
    tech = st.select_slider("Tech comfort", options=["low", "medium", "high"], value="medium")
    txn = st.selectbox("Transaction Type", ["B2C", "B2B", "Both"])

    if st.button("Find Best SNPs", type="primary"):
        ok, wait_seconds = _throttle_action("find_snps")
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before running matching again.")
            return
        t0 = time.perf_counter()
        try:
            cats = sorted({x.category_l1 for x in items}) or [cls["primary_l1"]]
            with st.spinner("🤝 SahayakMap is finding your match..."):
                st.session_state["snp_matches"] = s["engine"].match(profile, cats, tech_comfort=tech, transaction_type=txn, top_k=3)
            st.toast("SNP recommendations ready", icon="🤝")
            audit_event(
                "snp_match",
                status="success",
                udyam_masked=_mask_identifier(profile.udyam_number),
                result_count=len(st.session_state["snp_matches"]),
                transaction_type=txn,
            )
            _record_timing("last_match_seconds", time.perf_counter() - t0)
        except Exception as exc:
            audit_event("snp_match", status="error", error=str(exc))
            st.error(f"SNP matching failed: {exc}")

    matches = st.session_state["snp_matches"]
    if matches:
        st.info(s["engine"].get_match_summary(matches))
        for m in matches[:3]:
            snp = s["profiler"].get_snp_details(m.snp_id)
            icon = "🥇" if m.rank == 1 else "🥈" if m.rank == 2 else "🥉"
            with st.container(border=True):
                st.markdown(f"### {icon} {m.snp_name}")
                st.progress(float(m.overall_score), text=f"Overall score {m.overall_score:.2f}")
                st.markdown(
                    f"<span style='font-weight:700;color:{_score_color(float(m.overall_score))}'>"
                    f"Confidence: {float(m.overall_score):.2f}</span>",
                    unsafe_allow_html=True,
                )
                cols = st.columns(6)
                cols[0].metric("Domain", f"{m.domain_score:.2f}")
                cols[1].metric("Geo", f"{m.geography_score:.2f}")
                cols[2].metric("Lang", f"{m.language_score:.2f}")
                cols[3].metric("Cost", f"{m.cost_score:.2f}")
                cols[4].metric("Perf", f"{m.performance_score:.2f}")
                cols[5].metric("Tech", f"{m.tech_fit_score:.2f}")
                st.write("**Pros**")
                for p in m.pros:
                    st.write(f"✅ {p}")
                st.write("**Cons**")
                for c in m.cons:
                    st.write(f"⚠️ {c}")
                i1, i2, i3 = st.columns(3)
                i1.caption(f"Commission: {snp.commission_rate}%")
                i2.caption(f"Delivery: {', '.join(snp.geographic_coverage[:3])}")
                i3.caption(f"Platform: {snp.platform_type}")
                if st.button("Select This SNP", key=f"sel_{m.rank}"):
                    st.session_state["selected_snp"] = m.snp_id
                    st.session_state["onboarding_step"] = max(st.session_state["onboarding_step"], 5)
                    st.toast(f"Selected {m.snp_name}", icon="✅")
                    audit_event(
                        "snp_select",
                        status="success",
                        udyam_masked=_mask_identifier(profile.udyam_number),
                        snp_id=m.snp_id,
                        snp_name=m.snp_name,
                        rank=m.rank,
                    )

        st.dataframe(pd.DataFrame(s["engine"].compare_snps(matches)["comparison_table"]), use_container_width=True)
    else:
        st.info("No SNP matches yet. Run matching to see top recommendations.")

    if st.session_state["onboarding_step"] < 5:
        return

    st.markdown("### Step 5: Confirmation")
    snp_sel = st.session_state["selected_snp"]
    st.markdown(
        f"""
        <div class='card' style='border-left-color:#138808;'>
            <p><b>MSE:</b> {profile.enterprise_name} ({profile.udyam_number})</p>
            <p><b>Catalog items:</b> {len(items)}</p>
            <p><b>Selected SNP:</b> {snp_sel or 'Not selected yet'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Submit Registration", type="primary", use_container_width=True):
        ok, wait_seconds = _throttle_action("submit_registration")
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before submitting again.")
            return
        t0 = time.perf_counter()
        try:
            with st.spinner("Submitting registration package..."):
                reg = u["registration"].auto_register(profile.udyam_number, language=st.session_state["language"])
                reg = reg.model_copy(
                    update={
                        "preferred_snp_id": snp_sel,
                        "catalog_items": items,
                        "registration_status": "SNP_Assigned" if snp_sel else "Submitted",
                        "submitted_at": datetime.now(timezone.utc),
                    }
                )
                st.session_state["registered_package"] = reg
            _record_timing("last_registration_seconds", time.perf_counter() - t0)
            audit_event(
                "registration_submit",
                status="success",
                udyam_masked=_mask_identifier(profile.udyam_number),
                snp_id=snp_sel,
                catalog_count=len(items),
            )
            st.balloons()
            st.success("🎉 बधाई हो! Your MSE is being onboarded to ONDC!")
        except Exception as exc:
            audit_event("registration_submit", status="error", error=str(exc))
            st.error(f"Registration failed: {exc}")

    if st.session_state["registered_package"] is not None:
        registration = st.session_state["registered_package"]
        st.markdown("#### Next steps")
        st.checkbox("Registration submitted", value=True, disabled=True)
        st.checkbox("SNP onboarding initiated", value=bool(snp_sel), disabled=True)
        st.checkbox("Catalog quality verified", value=bool(items), disabled=True)

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.download_button(
                "Registration PDF",
                data=registration_pdf_bytes(registration),
                file_name=f"registration_{profile.udyam_number}.pdf",
                mime="application/pdf",
            )
        with d2:
            st.download_button(
                "Catalog PDF",
                data=catalog_pdf_bytes(items, profile),
                file_name=f"catalog_{profile.udyam_number}.pdf",
                mime="application/pdf",
            )
        with d3:
            st.download_button(
                "Catalog CSV",
                data=catalog_csv_bytes(items),
                file_name=f"catalog_{profile.udyam_number}.csv",
                mime="text/csv",
            )
        with d4:
            st.download_button(
                "ONDC JSON",
                data=catalog_ondc_json_bytes(items),
                file_name=f"catalog_{profile.udyam_number}.json",
                mime="application/json",
            )


def build_admin_analytics_data(
    funnel: FunnelAnalytics,
    geo: GeoAnalytics,
    women: WomenMSETracker,
) -> dict[str, Any]:
    summary_counts = funnel.get_funnel_summary()["counts"]
    monthly = (
        funnel.data.groupby("month", as_index=False)[["registered", "catalog_created", "snp_matched", "live", "first_order"]]
        .sum()
        .sort_values("month")
    )

    state_wise = (
        geo.mse_data.groupby("state", as_index=False)
        .agg(
            registered=("registered", "sum"),
            catalog_created=("catalog_created", "sum"),
            live=("live", "sum"),
            women_percentage=("is_women_owned", "mean"),
        )
        .sort_values("registered", ascending=False)
    )
    state_wise["women_percentage"] = state_wise["women_percentage"] * 100

    category_wise = (
        geo.mse_data.groupby("category_l1", as_index=False)
        .agg(mse_count=("mse_id", "count"), live_count=("live", "sum"))
        .sort_values("mse_count", ascending=False)
    )

    try:
        snp_perf = json.loads(data_path("snp_profiles", "snp_performance.json").read_text(encoding="utf-8"))
        if not isinstance(snp_perf, list):
            snp_perf = []
    except Exception:
        snp_perf = []
    snp_df = pd.DataFrame(snp_perf)
    snp_summary = {
        "total_snps": int(len(snp_df)),
        "avg_success_rate": float(snp_df["seller_success_rate"].mean()) if not snp_df.empty else 0.0,
        "avg_activation_days": float(snp_df["avg_activation_days"].mean()) if not snp_df.empty else 0.0,
    }

    women_pct = women.get_women_percentage() * 100
    analytics_data = {
        "summary": summary_counts,
        "state_wise": state_wise.to_dict(orient="records"),
        "category_wise": category_wise.to_dict(orient="records"),
        "women_mse": {
            "women_percentage": women_pct,
            "target_percentage": 50.0,
            "funnel": women.get_women_funnel(),
        },
        "snp_performance": snp_df.to_dict(orient="records"),
        "snp_performance_summary": snp_summary,
        "monthly_trends": monthly.to_dict(orient="records"),
        "bottleneck": funnel.get_bottleneck_analysis(),
    }
    return analytics_data


def admin_gate() -> bool:
    if st.session_state["admin_ok"]:
        return True

    remaining_lock = _admin_lock_remaining_seconds()
    if remaining_lock > 0:
        st.error(f"Admin access locked. Try again in {remaining_lock}s.")
        audit_event("admin_login_locked", status="blocked", remaining_seconds=remaining_lock)
        return False

    st.markdown("## Admin Access")
    pwd = st.text_input("Enter admin password", type="password")
    if st.button("Unlock Dashboard"):
        ok, wait_seconds = _throttle_action("admin_unlock", cooldown_seconds=1.0)
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before retrying.")
            return False

        provided_hash = _password_sha256(pwd)
        expected_hash = _expected_admin_hash()
        if hmac.compare_digest(provided_hash, expected_hash):
            st.session_state["admin_ok"] = True
            st.session_state["admin_fail_count"] = 0
            st.session_state["admin_lock_until"] = 0.0
            audit_event("admin_login", status="success")
            st.toast("Admin access granted", icon="🔓")
            return True

        st.session_state["admin_fail_count"] = int(st.session_state.get("admin_fail_count", 0)) + 1
        failed = st.session_state["admin_fail_count"]
        remaining_attempts = max(0, ADMIN_MAX_FAILED_ATTEMPTS - failed)

        if failed >= ADMIN_MAX_FAILED_ATTEMPTS:
            lock_until = time.time() + ADMIN_LOCKOUT_SECONDS
            st.session_state["admin_lock_until"] = lock_until
            st.session_state["admin_fail_count"] = 0
            audit_event(
                "admin_login",
                status="locked",
                lockout_seconds=ADMIN_LOCKOUT_SECONDS,
            )
            st.error(f"Too many failed attempts. Locked for {ADMIN_LOCKOUT_SECONDS}s.")
            return False

        audit_event(
            "admin_login",
            status="failed",
            remaining_attempts=remaining_attempts,
        )
        st.error(f"Invalid password. Remaining attempts: {remaining_attempts}")
    return False


def page_admin() -> None:
    if not admin_gate():
        return

    with st.spinner("📊 VriddhiDisha is analyzing..."):
        stack = vriddhidisha_stack()
    funnel: FunnelAnalytics = stack["funnel"]
    geo: GeoAnalytics = stack["geo"]
    women: WomenMSETracker = stack["women"]
    catalog: CatalogPerformance = stack["catalog"]
    prep: DashboardDataPrep = stack["prep"]

    st.markdown("## Admin Dashboard - VriddhiDisha")
    if geo.mse_data.empty:
        st.warning("No analytics data available. Generate synthetic data and retry.")
        return
    counts = funnel.get_funnel_summary()["counts"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Registered", f"{counts['registered']:,}")
    c2.metric("Catalog Created", f"{counts['catalog_created']:,}")
    c3.metric("SNP Matched", f"{counts['snp_matched']:,}")
    c4.metric("Live", f"{counts['live']:,}")
    c5.metric("First Order", f"{counts['first_order']:,}")

    st.markdown("### Women MSE Gauge")
    st.plotly_chart(women.get_women_target_gauge(), use_container_width=True)
    st.markdown("### Funnel")
    st.plotly_chart(funnel.get_funnel_chart(), use_container_width=True)

    analytics_data = build_admin_analytics_data(funnel, geo, women)
    e1, e2 = st.columns(2)
    with e1:
        st.download_button(
            "Download Admin PDF",
            data=admin_pdf_bytes(analytics_data),
            file_name="vyaparsetu_admin_report.pdf",
            mime="application/pdf",
        )
    with e2:
        st.download_button(
            "Download Admin Excel",
            data=admin_excel_bytes(analytics_data),
            file_name="vyaparsetu_admin_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    tabs = st.tabs(["Geographic", "Categories", "Women MSEs", "SNP Performance", "Monthly Trends", "Bottleneck Analysis"])
    with tabs[0]:
        render_map(geo.get_state_heatmap(), key="geo_state")
        options = ["All"] + sorted(geo.mse_data["state"].dropna().unique().tolist())
        selected = st.selectbox("Drill down state", options)
        render_map(geo.get_district_bubble_map(None if selected == "All" else selected), key="geo_dist")

    with tabs[1]:
        st.plotly_chart(catalog.get_category_distribution(str(data_path("synthetic", "products.csv"))), use_container_width=True)
        st.plotly_chart(catalog.get_pricing_analysis(str(data_path("synthetic", "products.csv"))), use_container_width=True)

    with tabs[2]:
        st.metric("Women-owned share", f"{women.get_women_percentage() * 100:.2f}%")
        st.plotly_chart(women.get_women_by_category(), use_container_width=True)
        wf = women.get_women_funnel()
        st.dataframe(pd.DataFrame([wf["women_conversion"], wf["other_conversion"]], index=["Women", "Others"]))
        st.markdown("**Recommendations**")
        for rec in women.get_recommendations():
            st.write(f"- {rec}")

    with tabs[3]:
        try:
            perf = pd.DataFrame(json.loads(data_path("snp_profiles", "snp_performance.json").read_text(encoding="utf-8")))
            st.bar_chart(perf.set_index("snp_id")[["seller_success_rate", "rating"]])
            st.dataframe(perf[["snp_id", "avg_activation_days", "active_sellers", "seller_success_rate", "rating"]], use_container_width=True)
        except Exception:
            st.info("SNP performance data unavailable")

    with tabs[4]:
        stage = st.selectbox("Stage", funnel.STAGES, index=0)
        st.plotly_chart(funnel.get_monthly_trend(stage), use_container_width=True)

    with tabs[5]:
        b = funnel.get_bottleneck_analysis()
        st.error(f"Worst stage: {b['worst_conversion_stage']} ({b['rate']*100:.2f}%)")
        st.info(f"Suggested action: {b['suggested_action']}")
        st.json(prep.get_overview_metrics())


def quick_preview(item: ONDCCatalogItem, formatter: ONDCFormatter) -> dict[str, Any]:
    payload = formatter.format_catalog_item(item)
    check = formatter.validate_catalog(payload)
    st.subheader(item.product_name_en)
    st.write(item.short_description)
    st.caption(f"ONDC Breadcrumb: {item.category_l1} > {item.category_l2} > {item.category_l3 or '-'}")
    st.caption(f"HSN {item.hsn_code} | INR {item.price_selling:.2f}")
    st.dataframe(pd.DataFrame([item.attributes]).T.rename(columns={0: "Value"}), use_container_width=True)
    if check["valid"]:
        st.success("ONDC JSON validation passed")
    else:
        st.error("ONDC JSON validation failed")
        for err in check["errors"]:
            st.write(f"- {err}")
    for warn in check["warnings"]:
        st.warning(warn)
    return payload


def page_prakriti() -> None:
    st.markdown("## Prakriti Assessment - Quick Catalog")
    st.caption("Standalone quick catalog builder without full registration. Type or speak and generate.")

    v = vastrasuchi_stack()
    enterprise = st.text_input("Enterprise name", value="Prakriti Demo Enterprise")
    desc = st.text_area("Describe your product")
    lang_options = list(SUPPORTED_LANGUAGES.keys())
    default_lang = st.session_state.get("language", lang_options[0] if lang_options else "en")
    if default_lang not in lang_options and lang_options:
        default_lang = lang_options[0]
    lang = st.selectbox("Language", lang_options, index=lang_options.index(default_lang) if lang_options else 0)
    mic_audio = _audio_input_widget("Or speak product details", key="prakriti_mic_audio")
    pics = st.file_uploader("Upload photos", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)

    if st.button("Generate Quick Catalog", type="primary"):
        ok, wait_seconds = _throttle_action("quick_catalog")
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before generating again.")
            return
        voice_text = _transcribe_audio(mic_audio, lang, udyambodh_stack()["bhashini"])
        final_desc = desc.strip() or voice_text.strip()
        if not final_desc:
            st.error("Please describe the product")
        else:
            try:
                profile = MSEProfile(
                    udyam_number="UDYAM-PR-00-0000001",
                    enterprise_name=enterprise,
                    owner_name="Owner",
                    owner_gender="Male",
                    enterprise_type="Micro",
                    major_activity="Manufacturing",
                    nic_2digit="10",
                    nic_5digit="10795",
                    nic_description="Manufacture of papads and similar foods",
                    state="Rajasthan",
                    district="Jaipur",
                    pincode="302001",
                    address="Jaipur",
                    mobile=None,
                    email=None,
                    date_of_incorporation=None,
                    date_of_udyam=None,
                    investment_plant=5.0,
                    turnover=20.0,
                    gstin=None,
                    pan=None,
                    social_category=None,
                    is_women_owned=False,
                    language_preference=lang,
                    products_services=[final_desc[:40]],
                )
                img_paths = []
                for pic in (pics or [])[:5]:
                    upload_path = ""
                    try:
                        upload_path = save_upload(pic)
                        validation = v["image"].validate_image(upload_path)
                        if validation.get("valid"):
                            img_paths.append(v["image"].process_product_image(upload_path))
                        else:
                            logger.info(
                                "Quick catalog skipped invalid image '%s': %s",
                                getattr(pic, "name", "upload"),
                                ", ".join(validation.get("issues", [])),
                            )
                    except Exception as exc:
                        logger.warning("Quick catalog image handling failed for '%s': %s", getattr(pic, "name", "upload"), exc)
                    finally:
                        if upload_path:
                            _safe_unlink(upload_path)
                req = ProductGenerationRequest(
                    mse_udyam=profile.udyam_number,
                    product_description_raw=final_desc,
                    product_images=img_paths,
                    language=lang,
                    category_hint=None,
                )
                with st.spinner("🛍️ VastraSuchi is building your catalog..."):
                    item = v["generator"].generate_catalog_item(req, profile)
                st.session_state["quick_items"].append(item)
                st.toast("Quick catalog generated", icon="⚡")
                audit_event(
                    "quick_catalog_generate",
                    status="success",
                    enterprise=enterprise[:60],
                    used_voice=bool(voice_text.strip()),
                    category_l1=item.category_l1,
                    hsn_code=item.hsn_code,
                )
            except Exception as exc:
                audit_event("quick_catalog_generate", status="error", error=str(exc))
                st.error(f"Quick catalog failed: {exc}")

    if not st.session_state["quick_items"]:
        st.info("No quick catalog items yet. Generate one to download PDF/CSV/ONDC JSON.")

    for i, item in enumerate(st.session_state["quick_items"]):
        with st.container(border=True):
            quick_preview(item, v["formatter"])
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button(
                    f"Download PDF #{i+1}",
                    data=catalog_pdf_bytes([item], item_to_demo_mse(item, enterprise)),
                    file_name=f"ondc_item_{i+1}.pdf",
                    mime="application/pdf",
                    key=f"qd_pdf_{i}",
                )
            with d2:
                st.download_button(
                    f"Download CSV #{i+1}",
                    data=catalog_csv_bytes([item]),
                    file_name=f"ondc_item_{i+1}.csv",
                    mime="text/csv",
                    key=f"qd_csv_{i}",
                )
            with d3:
                st.download_button(
                    f"Download ONDC JSON #{i+1}",
                    data=catalog_ondc_json_bytes([item]),
                    file_name=f"ondc_item_{i+1}.json",
                    mime="application/json",
                    key=f"qd_json_{i}",
                )


def page_competition() -> None:
    st.markdown("## Competition Readiness")
    st.caption("Submission-grade evidence bundle for jury review and governance checks.")

    outputs = _read_submission_outputs()
    score = outputs.get("score", {})
    security = outputs.get("security", {})
    reference = outputs.get("reference", {})
    demo = outputs.get("demo", {})

    if st.button("Generate Submission Pack", type="primary", use_container_width=True):
        ok, wait_seconds = _throttle_action("generate_submission_pack", cooldown_seconds=2.0)
        if not ok:
            st.warning(f"Please wait {wait_seconds:.1f}s before generating again.")
        else:
            with st.spinner("Building submission evidence bundle..."):
                result = generate_submission_pack()
            if result.get("status") == "ok":
                st.success("Submission pack generated successfully.")
                st.toast("Evidence bundle ready", icon="📦")
            else:
                st.error("Failed to generate submission pack.")
            outputs = _read_submission_outputs()
            score = outputs.get("score", {})
            security = outputs.get("security", {})
            reference = outputs.get("reference", {})
            demo = outputs.get("demo", {})

    if score:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Score", f"{score.get('overall_score', 0)}/100")
        c2.metric("Band", str(score.get("readiness_band", "N/A")))
        c3.metric("Reference Data", str(score.get("reference_data_score", 0)))
        c4.metric("Security", str(score.get("security_score", 0)))
    else:
        st.info("Generate the submission pack to view readiness scorecards.")

    st.markdown("### Governance & Compliance")
    rc1, rc2 = st.columns(2)
    with rc1:
        st.write("**Reference Data Integrity**")
        if reference:
            for key, ok in reference.items():
                st.write(f"- {'PASS' if ok else 'FAIL'} {key}")
        else:
            st.write("- No validation snapshot yet.")
    with rc2:
        st.write("**Security Controls**")
        if security:
            st.write(f"- Admin hash configured: `{security.get('admin_hash_configured')}`")
            st.write(f"- Lockout seconds: `{security.get('admin_lockout_seconds')}`")
            st.write(f"- Max failed attempts: `{security.get('admin_max_failed_attempts')}`")
            st.write(f"- Action cooldown seconds: `{security.get('action_cooldown_seconds')}`")
            st.write(f"- Audit log: `{security.get('audit_log_path')}`")
        else:
            st.write("- No security snapshot yet.")

    st.markdown("### Demo Reliability")
    if demo:
        scene4 = demo.get("scene_4", {}) if isinstance(demo, dict) else {}
        d1, d2, d3 = st.columns(3)
        d1.metric("Demo Status", str(demo.get("status", "unknown")))
        d2.metric("Synthetic MSEs", f"{scene4.get('total_mses', 'N/A')}")
        d3.metric("Women %", f"{scene4.get('women_percentage', 'N/A')}%")
    else:
        st.write("No demo summary yet.")

    zip_path = Path(outputs.get("zip_path", ""))
    if zip_path.exists():
        st.download_button(
            "Download Submission ZIP",
            data=zip_path.read_bytes(),
            file_name=zip_path.name,
            mime="application/zip",
            use_container_width=True,
        )
        st.caption(f"Bundle: `{zip_path}`")
    else:
        st.caption("Submission ZIP will appear after generation.")


def page_about() -> None:
    st.markdown("## About")
    st.write(
        "VyaparSetu helps micro and small enterprises move from Udyam registration "
        "to ONDC activation using assisted onboarding, catalog AI, SNP matching, and growth analytics."
    )
    st.markdown("### Architecture")
    st.code(
        """
MSE Input (Udyam/Voice/Text)
 -> UdyamBodh (profile + classification)
 -> VastraSuchi (catalog + ONDC format)
 -> SahayakMap (SNP ranking)
 -> VriddhiDisha (analytics)
 -> TEAM/ONDC onboarding package
        """.strip(),
        language="text",
    )
    st.markdown("### Team")
    st.write("TEAM Initiative - MSME digital enablement collaboration")
    st.markdown("### Technology Stack")
    st.write("Streamlit, FastAPI, PostgreSQL, Ollama, Pandas, Plotly, Folium, SQLAlchemy")
    st.markdown("### Government Integration Points")
    st.write("Udyam, GST, Bhashini, ONDC taxonomy/network")
    st.markdown("### Privacy Policy Summary")
    st.write("Only essential onboarding data is processed; analytics views rely on synthetic/aggregated reporting.")

    st.markdown("### Contact / Feedback")
    with st.form("feedback"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        msg = st.text_area("Feedback")
        ok = st.form_submit_button("Submit")
        if ok:
            if msg.strip():
                st.success("Thank you. Feedback received.")
                st.caption(f"Reference: {name or 'Anonymous'} | {email or 'No email'}")
            else:
                st.error("Please enter feedback before submitting")


def main() -> None:
    st.set_page_config(page_title="VyaparSetu - व्यापारसेतु", page_icon="🏪", layout="wide")
    apply_styles()
    init_state()

    page = sidebar()
    try:
        if page == "home":
            page_home()
        elif page == "register":
            page_register()
        elif page == "admin":
            page_admin()
        elif page == "prakriti":
            page_prakriti()
        elif page == "competition":
            page_competition()
        elif page == "about":
            page_about()
    except Exception as exc:
        logger.exception("Unhandled app error")
        audit_event("app_unhandled_error", status="error", error=str(exc))
        st.error(f"Unexpected error handled safely: {exc}")
        st.info("The app is still running in safe mode. You can continue navigating or restart the current flow.")


if __name__ == "__main__":
    main()

