## Slide 1: Title
VyaparSetu (व्यापारसेतु)
From Udyam to ONDC - AI that onboards India's MSEs
IndiaAI Innovation Challenge 2026 | Problem Statement 2
Team Name: [FILL]

## Slide 2: The Problem
- 6.3 crore MSMEs in India, <5% are digitally onboarded to ONDC
- Manual data entry, inconsistent category tagging, language barriers
- Labour-intensive NSIC claim verification causes delays
- Current TEAM initiative workflow is largely manual

## Slide 3: Our Solution - VyaparSetu
- End-to-end AI platform: Udyam number in, ONDC-ready catalog out
- 4 integrated modules: UdyamBodh, VastraSuchi, SahayakMap, VriddhiDisha
- Voice-first, multilingual (8 Indian languages via Bhashini)
- Works offline in demo mode, full deployment via Docker

## Slide 4: How It Works (Flow)
1. MSE speaks/types Udyam number -> UdyamBodh fetches & validates
2. Products described in local language -> VastraSuchi generates ONDC catalog
3. SahayakMap recommends best SNP with explainable 6-dimension scoring
4. VriddhiDisha admin dashboard tracks funnel, geography, women MSE goals
(Reference the architecture diagram from outputs/architecture_diagram.png)

## Slide 5: UdyamBodh - Smart Registration
- Auto-fetch from Udyam API with GST validation
- OCR fallback for scanned certificates (PaddleOCR)
- NIC-to-ONDC business classification (hybrid keyword + LLM)
- TEAM portal registration package generation

## Slide 6: VastraSuchi - AI Catalog Generation
- Product classification to ONDC L1/L2/L3 taxonomy (10 categories, 230 HSN codes)
- HSN code mapping with confidence scoring
- AI-powered pricing suggestions (category + quantity + premium factors)
- ONDC schema validation and multi-format export (JSON, CSV, PDF)

## Slide 7: SahayakMap - Explainable SNP Matching
- 6-dimensional scoring: Domain (30%), Geography (20%), Language (15%), Cost (15%), Performance (10%), Tech Fit (10%)
- Top-3 SNP recommendations with natural-language explanations
- 26 real SNP profiles with performance data
- Multi-language explanations (Hindi, Tamil, Gujarati, English)

## Slide 8: VriddhiDisha - Growth Analytics Dashboard
- Onboarding funnel tracking (5 stages)
- Geographic heatmaps (state/district level with Folium)
- Women MSE tracker with 50% TEAM target gauge
- Catalog quality scoring and bottleneck identification

## Slide 9: Voice-First & Multilingual
- Bhashini integration for ASR/TTS across 8 languages
- Conversational onboarding engine (guided dialogue flow)
- MSME-specific vocabulary normalization
- Works for low-literacy MSE owners

## Slide 10: Technical Architecture
- Stack: Python 3.11, Streamlit, Ollama (llama3.1:8b), PostgreSQL/SQLite, Docker
- Modular: each module independently testable
- 43 automated tests, CI via GitHub Actions
- Demo mode with synthetic data (5000 MSEs, 2000 products, 36 states)
- Privacy-by-design aligned with DPDP Act 2023

## Slide 11: Model Performance
- Product Classifier Accuracy: [FILL from evaluation]%
- Macro-F1 Score: [FILL]
- SNP Matching Top-3 Accuracy: [FILL]%
- Mean Reciprocal Rank: [FILL]
- Inference Latency: <2s per classification (demo mode)
- 230 HSN codes, 99 NIC divisions, 26 SNP profiles validated

## Slide 12: Responsible AI & Data Governance
- Minimal data collection (Udyam + product descriptions only)
- Synthetic datasets for demos - no real PII
- SHA-256 admin authentication with lockout controls
- Audit logging for all sensitive actions
- Explainable AI: every SNP recommendation has human-readable reasoning
- Women MSE inclusion tracking (50% TEAM target)

## Slide 13: Scalability & Deployment Roadmap
- TRL 6: System demonstrated in relevant environment
- Docker Compose: one-command deployment (Streamlit + PostgreSQL + Ollama + Qdrant + Redis)
- Phase 1 (0-6 months): Pilot with 3 states, 1000 MSEs
- Phase 2 (6-12 months): Scale to 15 states, integrate live Udyam + Bhashini APIs
- Phase 3 (12-24 months): National rollout, real-time ONDC network integration

## Slide 14: Business Model
- B2G: Government deployment under TEAM initiative
- Transaction fees: Small commission on successful ONDC onboarding
- SaaS tier: Premium analytics for SNPs and state MSME departments
- Open-source core with enterprise support

## Slide 15: Team
[FILL team members, roles, LinkedIn, prior experience]

## Slide 16: Ask
- INR 25 Lakhs for pilot phase refinement
- Access to live Udyam/ONDC APIs via IndiaAI
- Partnership with NSIC for TEAM initiative integration
- Path to INR 1 Crore work contract for national deployment
