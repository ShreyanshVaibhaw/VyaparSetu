# VyaparSetu - व्यापारसेतु
## From Udyam to ONDC - AI that onboards India's MSEs

VyaparSetu is a full-stack onboarding and intelligence platform for micro and small enterprises (MSEs). It automates business intake, generates ONDC-ready catalogs, recommends the right Seller Network Participant (SNP), and provides admin analytics aligned with TEAM Initiative goals.

## Quick Start
Docker:
`./setup.sh` -> http://localhost:8501

Local:
`./setup_local.sh` -> http://localhost:8501

Local (Windows PowerShell):
`.\setup_local.ps1` -> http://localhost:8501

Demo only:
`python scripts/demo_flow.py`

## Architecture
```text
MSE -> Phone/Web -> VyaparSetu
  -> UdyamBodh -> Udyam API/GST -> TEAM Portal package
  -> VastraSuchi -> ONDC Catalog (JSON/CSV/PDF)
  -> SahayakMap -> SNP Selection (Top-3 explainable)
  -> VriddhiDisha -> Admin Dashboard (funnel/geo/women)
```

## Modules
- `UdyamBodh`: Smart registration engine, Udyam fetch, GST checks, OCR fallback, business classification.
- `VastraSuchi`: AI-assisted ONDC catalog generation with category mapping, HSN mapping, and pricing.
- `SahayakMap`: Explainable SNP matching based on domain, geography, language, cost, performance, and tech fit.
- `VriddhiDisha`: Growth dashboard with funnel, geo, catalog, and women-owned MSE analytics.

## Tech Stack
- `Python 3.11`, `Streamlit`, `FastAPI`
- `Pandas`, `NumPy`, `Plotly`, `Folium`
- `SQLAlchemy`, `PostgreSQL` with `SQLite` fallback
- `Ollama` for local LLM inference
- `Docker`, `Docker Compose`

## Government Integration
- `Udyam`: enterprise profile intake and registration identifiers
- `ONDC`: taxonomy-aligned catalog generation and SNP onboarding support
- `TEAM Initiative`: workflow and reporting alignment
- `Bhashini`: multilingual speech and language support
- `GST`: GSTIN format/state validation

## Privacy
VyaparSetu is designed with privacy-by-default principles aligned with India’s DPDP Act expectations:
- Minimal data collection for onboarding use-cases
- Purpose-limited processing for registration and analytics
- Synthetic and aggregated datasets for demos and admin insights
- Local/offline demo mode for controlled evaluations

## Runtime Modes
- `FULL`: Docker + Ollama + PostgreSQL (best experience)
- `PARTIAL`: Ollama only with SQLite/in-memory fallback behavior
- `DEMO`: No external services; cached responses and synthetic data
- Sidebar controls: language selection (`Hindi/English/...`) and UI theme (`Professional Light`, `Executive Dark`, `High Contrast`)

## Competition Readiness
- New dashboard page: `Competition Readiness` in Streamlit for jury-facing scorecards.
- One-click evidence bundle generation from app or CLI:
`python scripts/generate_submission_pack.py`
- Bundle includes:
  - `submission_overview.md`
  - `runtime_snapshot.json`
  - `reference_validation.json`
  - `demo_summary.json`
  - `security_snapshot.json`
  - `readiness_score.json`
  - zipped as `outputs/submission/vyaparsetu_submission_pack.zip`

## Security Hardening
- Admin auth supports `VYAPARSETU_ADMIN_PASSWORD_HASH` (SHA-256) in addition to plain password env.
- Admin login has lockout controls:
`VYAPARSETU_ADMIN_MAX_FAILED_ATTEMPTS`, `VYAPARSETU_ADMIN_LOCKOUT_SECONDS`.
- UI action throttling prevents rapid repeated expensive operations:
`VYAPARSETU_ACTION_COOLDOWN_SECONDS`.
- Structured audit logs are written to `outputs/logs/audit.log` (override with `VYAPARSETU_AUDIT_LOG`).
- Recommended: set a strong admin hash in `.env` and avoid default credentials in shared environments.

## CI
GitHub Actions workflow runs:
- `python scripts/validate_reference_data.py`
- `pytest -q -p no:cacheprovider`
- `python -m compileall -q src tests app.py scripts config.py`

Local verification:
- `python -m pytest -q -p no:cacheprovider`
- `python -m compileall -q src tests app.py scripts config.py`

## Validation Utilities
- Reference data checks: `python scripts/validate_reference_data.py`
- Narrated demo script: `python scripts/demo_video_script.py`
- Admin password hash helper: `python scripts/generate_admin_password_hash.py`
- Submission bundle generator: `python scripts/generate_submission_pack.py`
