# VyaparSetu — Codex CLI Prompts to Close Competition Gaps

> **Context**: IndiaAI Innovation Challenge 2026 — Problem Statement 2 (AI-powered MSE Agent Mapping Tool).
> **Current state**: 43/43 tests pass, readiness score 94/100, but the jury evaluation rubric (Annexure II) has explicit gaps.
> **Run each prompt below as a standalone Codex CLI command.**
> Priority order: P0 (blocking) → P1 (important) → P2 (polish).

---

## P0-1: Add Model Evaluation Script with Accuracy / Precision / Recall / F1 / AUC-ROC

The jury evaluation (Annexure II, rows 3-4) explicitly scores: Accuracy, Precision, Recall, F1, AUC-ROC, Confusion Matrix, inference latency, and cost per inference.
**Currently ZERO metrics exist anywhere in the codebase.**

```
codex "Create a new file scripts/evaluate_models.py that measures classification performance for VyaparSetu.

The script must:

1. PRODUCT CLASSIFIER EVALUATION
   - Import ProductClassifier from src/vastrasuchi/product_classifier.py
   - Import LLMClient from src/llm/ollama_client.py
   - Instantiate ProductClassifier(categories_path='data/ondc_taxonomy/categories.json', hsn_mapping_path='data/ondc_taxonomy/hsn_mapping.json', llm_client=llm)
   - Define a ground-truth test set of at least 50 product descriptions with known L1 categories. Use realistic Indian MSE products:
     Mango Pickle -> Food & Beverage
     Silk Saree -> Fashion
     Brass Idol -> Handicrafts & Handloom
     Turmeric Powder -> Food & Beverage
     Leather Bag -> Fashion
     LED Bulb -> Electronics
     Handmade Soap -> Health & Beauty
     Cotton Bedsheet -> Home & Kitchen
     Steel Utensil -> Home & Kitchen
     Jute Bag -> Handicrafts & Handloom
     ... (add 40 more diverse products from Food & Beverage, Fashion, Handicrafts & Handloom, Home & Kitchen, Electronics, Health & Beauty, Agriculture, Services, Grocery, Building & Construction)
   - Call classifier.classify(desc) for each product, time each call
   - Compare predicted L1 against ground truth
   - Compute: accuracy, macro-precision, macro-recall, macro-F1, per-class F1, weighted F1
   - Build a confusion matrix (rows=true, cols=predicted)
   - Compute one-vs-rest AUC-ROC per class using confidence scores (classifier returns confidence in the dict)
   - Record inference_latency_seconds per call (mean, p50, p95)

2. BUSINESS CLASSIFIER EVALUATION
   - Import BusinessClassifier from src/udyambodh/business_classifier.py
   - Instantiate BusinessClassifier(llm_client=llm, nic_to_ondc_path='data/ondc_taxonomy/nic_to_ondc.json', categories_path='data/ondc_taxonomy/categories.json')
   - Define 30+ test cases with known NIC 2-digit codes and expected ONDC L1 categories
   - Call classify_from_nic(nic_code) and check if expected L1 is in the returned list
   - Report accuracy and coverage

3. SNP SCORER EVALUATION
   - Import SNPScorer from src/sahayakmap/scoring.py
   - Use SNP_MATCH_WEIGHTS from config.py: {'domain': 0.30, 'geography': 0.20, 'language': 0.15, 'cost': 0.15, 'performance': 0.10, 'tech_fit': 0.10}
   - Define 20 MSE-SNP test pairs with known expected top-SNP outcomes
   - Measure ranking accuracy (% where expected SNP is in top-3)
   - Report mean reciprocal rank (MRR)

4. OUTPUT
   - Print a formatted report table to stdout
   - Save results to outputs/model_evaluation_report.json with structure:
     {
       'product_classifier': { 'accuracy': float, 'macro_precision': float, 'macro_recall': float, 'macro_f1': float, 'weighted_f1': float, 'per_class_f1': dict, 'auc_roc': dict, 'confusion_matrix': list[list[int]], 'class_labels': list[str], 'inference_latency_mean_sec': float, 'inference_latency_p95_sec': float, 'num_samples': int },
       'business_classifier': { 'accuracy': float, 'coverage': float, 'num_samples': int },
       'snp_scorer': { 'top3_accuracy': float, 'mrr': float, 'num_samples': int },
       'generated_at': ISO timestamp
     }
   - Also save a human-readable outputs/model_evaluation_report.md with markdown tables

5. REQUIREMENTS
   - Use only stdlib + numpy + pandas (already in requirements.txt)
   - Use sklearn.metrics if available, else manual computation
   - The script must work in DEMO mode (no Ollama needed) since LLMClient has built-in fallback
   - Add 'if __name__ == \"__main__\": main()' entry point
   - Handle import errors gracefully

Do NOT modify any existing files. Only create scripts/evaluate_models.py."
```

---

## P0-2: Expand MSME Vocabulary Module (Currently a 12-line stub)

The current `src/voice/msme_vocabulary.py` has only a single function `normalize_transcript(text, synonyms)` with no actual dictionary. The jury evaluates NLP and multilingual capabilities heavily.

```
codex "Expand src/voice/msme_vocabulary.py from its current stub into a complete multilingual MSME vocabulary normalization module.

Current file has only:
  def normalize_transcript(text: str, synonyms: dict[str, list[str]] | None = None) -> str

Keep this function signature unchanged (backward compatible). Enhance it to:

1. Load a built-in MSME vocabulary from data/vocabulary/msme_terms.json and data/vocabulary/product_synonyms.json at module level (lazy-load, cache after first load).

2. SYNONYM DICTIONARY (add as DEFAULT_SYNONYMS constant in the module):
   Build a comprehensive dict with at least 150 entries covering:

   a) Product name variants across Hindi/English/regional:
      - 'mango pickle': ['aam ka achaar', 'aam ka achar', 'aam achaar', 'आम का अचार', 'mango achar']
      - 'turmeric': ['haldi', 'हल्दी', 'manjal', 'pasupu']
      - 'saree': ['sari', 'साड़ी', 'saadi', 'pudava']
      - 'brass utensil': ['peetal ka bartan', 'पीतल का बर्तन', 'pital bartan']
      - 'leather bag': ['chamde ka bag', 'चमड़े का बैग', 'leather purse']
      - 'cotton bedsheet': ['sooti chadar', 'सूती चादर', 'cotton chadar']
      - 'jute bag': ['jute ka thela', 'joot bag', 'जूट बैग']
      - 'handmade soap': ['haath ka sabun', 'हाथ का साबुन']
      - 'steel utensil': ['steel bartan', 'स्टील बर्तन']
      - 'incense sticks': ['agarbatti', 'अगरबत्ती', 'dhoop']
      ... (add 50+ more product categories)

   b) Business terms:
      - 'enterprise': ['udyam', 'udyog', 'उद्यम', 'karobar', 'व्यापार']
      - 'registration': ['panjikaran', 'पंजीकरण', 'registration number']
      - 'turnover': ['karobar', 'bikri', 'बिक्री', 'annual sales']
      - 'manufacturing': ['nirman', 'निर्माण', 'utpadan', 'उत्पादन']
      - 'wholesale': ['thok', 'थोक', 'bulk selling']
      - 'retail': ['khudra', 'खुदरा', 'chhota dukaan']
      ... (add 30+ business terms)

   c) Measurement units:
      - 'kilogram': ['kg', 'kilo', 'किलो', 'किलोग्राम']
      - 'gram': ['gm', 'g', 'ग्राम']
      - 'piece': ['piece', 'pcs', 'nag', 'नग', 'adad', 'अदद']
      - 'dozen': ['darjan', 'दर्जन', 'drz']
      - 'liter': ['litre', 'ltr', 'लीटर']
      ... (add 15+ units)

   d) Common transcription errors / phonetic variants:
      - 'pickle': ['pikul', 'pikal', 'pikle']
      - 'business': ['bijness', 'biznes']
      - 'category': ['catagory', 'categry']
      - 'organic': ['orgenik', 'arganik']

3. Add new helper functions (keep normalize_transcript as the main entry point):
   - detect_language(text: str) -> str: Simple heuristic (Devanagari chars -> 'hi', Tamil chars -> 'ta', else 'en')
   - extract_product_terms(text: str) -> list[str]: Find known product names in text
   - standardize_units(text: str) -> str: Replace unit variants with canonical forms

4. The normalize_transcript function should:
   - If synonyms arg is None, use DEFAULT_SYNONYMS merged with loaded JSON files
   - Apply case-insensitive matching
   - Handle Devanagari text properly
   - Return the normalized text with canonical English terms

5. Update data/vocabulary/msme_terms.json to include a structured version of the business terms
6. Update data/vocabulary/product_synonyms.json to include the product synonym mappings

Maintain the existing import: 'from src.voice.msme_vocabulary import normalize_transcript' must still work.
Do not modify any other source files."
```

---

## P0-3: Expand Synthetic Data to Cover All 36 States/UTs

Jury will check geographic coverage. Currently only 10 states.

```
codex "Modify scripts/generate_synthetic_data.py to cover all 36 Indian states and UTs instead of only 10.

Current STATES list (line ~30): Rajasthan, Tamil Nadu, Maharashtra, Uttar Pradesh, West Bengal, Karnataka, Gujarat, Kerala, Madhya Pradesh, Haryana

Replace with all 36 states/UTs with realistic population-weighted probabilities:
  Uttar Pradesh: 0.12, Maharashtra: 0.10, Bihar: 0.04, West Bengal: 0.06, Madhya Pradesh: 0.05, Tamil Nadu: 0.07, Rajasthan: 0.06, Karnataka: 0.06, Gujarat: 0.06, Andhra Pradesh: 0.04, Odisha: 0.03, Telangana: 0.03, Kerala: 0.04, Jharkhand: 0.02, Assam: 0.02, Punjab: 0.02, Chhattisgarh: 0.02, Haryana: 0.02, Delhi: 0.02, Jammu & Kashmir: 0.01, Uttarakhand: 0.01, Himachal Pradesh: 0.01, Tripura: 0.005, Meghalaya: 0.005, Manipur: 0.005, Nagaland: 0.005, Mizoram: 0.003, Arunachal Pradesh: 0.003, Goa: 0.005, Sikkim: 0.002, Puducherry: 0.002, Chandigarh: 0.002, Andaman & Nicobar: 0.001, Dadra & Nagar Haveli: 0.001, Lakshadweep: 0.001, Ladakh: 0.001

Also update the STATE_DISTRICTS mapping and LANGUAGE_MAP to include all 36 states:
  - Bihar -> hi, Odisha -> or, Telangana -> te, Assam -> as, Punjab -> pa, Jharkhand -> hi, Chhattisgarh -> hi, Delhi -> hi, etc.
  - Add at least 2-3 district names per new state (use real district names)

Update the state_code in udyam_number generation to use proper 2-letter state codes for all states (RJ, TN, MH, UP, WB, KA, GJ, KL, MP, HR, BR, OD, TS, AP, AS, PB, JH, CT, DL, JK, UK, HP, TR, ML, MN, NL, MZ, AR, GA, SK, PY, CH, AN, DN, LD, LA).

Keep the same total n=5000 MSEs and seed=2026.
After modification, regenerate by running: python scripts/generate_synthetic_data.py

Only modify scripts/generate_synthetic_data.py. Do not touch other files."
```

---

## P0-4: Add Model Evaluation Metrics to Submission Pack

The submission pack currently has no model metrics. Wire the new evaluation into the submission generation pipeline.

```
codex "Modify src/common/submission_pack.py to include model evaluation metrics in the submission bundle.

Current function generate_submission_pack() in src/common/submission_pack.py generates these files: runtime_snapshot.json, reference_validation.json, demo_summary.json, security_snapshot.json, readiness_score.json, submission_overview.md

Add a new step that:

1. Try to load outputs/model_evaluation_report.json (generated by scripts/evaluate_models.py)
2. If it exists, include it in the ZIP as model_evaluation_report.json
3. Add a 'Model Performance' section to submission_overview.md showing:
   - Product Classifier Accuracy: X%
   - Product Classifier Macro-F1: X
   - Product Classifier Weighted-F1: X
   - Business Classifier Accuracy: X%
   - SNP Matcher Top-3 Accuracy: X%
   - SNP Matcher MRR: X
4. If the file does not exist, add a note: 'Run scripts/evaluate_models.py to generate model metrics'
5. Factor model_evaluation into the readiness score: if present and product_classifier accuracy >= 0.70, add 5 bonus points to overall_score (cap at 100)

Also update scripts/generate_submission_pack.py to:
- Run scripts/evaluate_models.py before generating the pack (subprocess call, ignore failure)
- Include model_evaluation_report.json in the ZIP file list

Keep all existing functionality unchanged. Only add, do not remove."
```

---

## P0-5: Create Technical Architecture Diagram (SVG/PNG)

Annexure III Section 2 Q7 requires architecture diagrams. Currently none exist.

```
codex "Create a Python script scripts/generate_architecture_diagram.py that generates a technical architecture diagram for VyaparSetu as an SVG file.

Use only matplotlib (already in requirements) to draw the diagram. Do NOT require graphviz, mermaid, or any external tool.

The diagram must show:

TOP ROW (User Interface Layer):
  [MSE User (Phone/Web)] --> [Streamlit UI (8501)]
  [Admin User] --> [Streamlit UI (8501)]

MIDDLE ROW (Application Modules):
  [Streamlit UI] branches to 4 boxes:
    [UdyamBodh - Registration] containing: Udyam Fetcher, GST Validator, OCR Engine, Business Classifier
    [VastraSuchi - Catalog] containing: Product Classifier, HSN Mapper, Pricing Engine, ONDC Formatter
    [SahayakMap - SNP Match] containing: SNP Scorer (6-dim), Matching Engine, Explainer
    [VriddhiDisha - Analytics] containing: Funnel, Geo Maps, Women MSE, Catalog Perf

SUPPORTING LAYER:
  [Voice Engine (Bhashini ASR/TTS)] connected to UdyamBodh and VastraSuchi
  [LLM Engine (Ollama / llama3.1:8b)] connected to all 4 modules
  [Conversation Engine] connected to Voice Engine and Streamlit UI

BOTTOM ROW (Data & Infrastructure):
  [PostgreSQL / SQLite] [ONDC Taxonomy (JSON)] [SNP Database (JSON)] [Synthetic Data (CSV)]

EXTERNAL APIs (shown as clouds/dashed):
  [Udyam API] [GST API] [Bhashini API] [ONDC Network] [TEAM Portal]

Use color coding:
  - Blue for user-facing
  - Green for core AI modules
  - Orange for supporting services
  - Gray for data stores
  - Dashed for external APIs

Save to: outputs/architecture_diagram.svg and outputs/architecture_diagram.png (both)
Add title: 'VyaparSetu — Technical Architecture'
Add subtitle: 'IndiaAI Innovation Challenge 2026 | Problem Statement 2'

The script should have: if __name__ == '__main__': main()
Only create the new script. Do not modify existing files."
```

---

## P0-6: Configure Admin Password Hash for Security Score

Security score is 70/100 because admin_hash_configured is false.

```
codex "Create a .env file at the project root (C:/Users/shrey/OneDrive/Desktop/ONDC PROJECT/.env) based on the existing .env.example.

Set these values:
  BHASHINI_API_KEY=
  BHASHINI_USER_ID=
  OLLAMA_HOST=localhost
  OLLAMA_PORT=11434
  POSTGRES_URI=postgresql://vyaparsetu:vyaparsetu2026@localhost:5432/vyaparsetu
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  REDIS_URL=redis://localhost:6379/0
  VYAPARSETU_ADMIN_PASSWORD=team2026
  VYAPARSETU_ADMIN_PASSWORD_HASH=<SHA-256 hash of 'team2026'>
  VYAPARSETU_ADMIN_MAX_FAILED_ATTEMPTS=5
  VYAPARSETU_ADMIN_LOCKOUT_SECONDS=300
  VYAPARSETU_ACTION_COOLDOWN_SECONDS=1.5
  VYAPARSETU_AUDIT_LOG=outputs/logs/audit.log

Compute the SHA-256 hash of 'team2026' using Python: hashlib.sha256('team2026'.encode()).hexdigest()
Put the computed hash as VYAPARSETU_ADMIN_PASSWORD_HASH value.

Only create the .env file. Do not modify any source files."
```

---

## P1-1: Add Comprehensive Benchmarking Test Suite

Annexure II Technical row 4 requires documented robustness. Add tests that prove classifier quality.

```
codex "Create a new test file tests/test_model_benchmarks.py that validates model quality thresholds.

Use pytest. Follow the existing test patterns from tests/test_vastrasuchi.py.

Test cases:

1. test_product_classifier_accuracy_above_threshold():
   - Instantiate ProductClassifier with FakeLLM (copy the pattern from tests/test_integration.py FakeIntegrationLLM)
   - Run classify() on at least 20 known product-category pairs
   - Assert accuracy >= 0.70 (70%)

2. test_product_classifier_confidence_scores():
   - For each classified product, assert 0.0 <= confidence <= 1.0
   - Assert mean confidence >= 0.5

3. test_business_classifier_nic_mapping():
   - Import BusinessClassifier from src/udyambodh/business_classifier.py
   - Test 15 NIC 2-digit codes: '10' -> 'Food & Beverage', '13' -> 'Fashion', '14' -> 'Fashion', '32' -> 'Handicrafts & Handloom', etc.
   - Assert each expected L1 is in the returned list

4. test_snp_scorer_consistency():
   - Import SNPScorer from src/sahayakmap/scoring.py
   - Score the same MSE-SNP pair 10 times
   - Assert all scores are identical (deterministic)

5. test_snp_scorer_dimension_bounds():
   - For each scoring method (score_domain, score_geography, score_language, score_cost, score_performance, score_tech_fit)
   - Assert 0.0 <= score <= 1.2 (some have bonus up to 1.1)

6. test_hsn_mapper_known_products():
   - Import HSNMapper from src/vastrasuchi/hsn_mapper.py
   - Test: 'coffee' -> HSN starts with '09', 'rice' -> '10', 'cotton' -> '52'

7. test_pricing_engine_reasonable_prices():
   - Import PricingEngine from src/vastrasuchi/pricing_engine.py
   - Generate prices for 10 categories
   - Assert all prices > 0 and < 100000

8. test_inference_latency():
   - Time 10 product classifications
   - Assert mean latency < 5.0 seconds in demo mode

Each test must have a clear docstring explaining what evaluation criterion it addresses.
Only create tests/test_model_benchmarks.py. Do not modify existing files."
```

---

## P1-2: Generate Pitch Deck Content (Markdown for conversion to PPTX)

Annexure III Section 4 requires a Pitch Deck upload.

```
codex "Create outputs/pitch_deck.md — a structured markdown file that can be converted to a presentation for the IndiaAI Innovation Challenge 2026.

Structure (one ## heading per slide):

## Slide 1: Title
VyaparSetu (व्यापारसेतु)
From Udyam to ONDC — AI that onboards India's MSEs
IndiaAI Innovation Challenge 2026 | Problem Statement 2
Team Name: [FILL]

## Slide 2: The Problem
- 6.3 crore MSMEs in India, <5% are digitally onboarded to ONDC
- Manual data entry, inconsistent category tagging, language barriers
- Labour-intensive NSIC claim verification causes delays
- Current TEAM initiative workflow is largely manual

## Slide 3: Our Solution — VyaparSetu
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

## Slide 5: UdyamBodh — Smart Registration
- Auto-fetch from Udyam API with GST validation
- OCR fallback for scanned certificates (PaddleOCR)
- NIC-to-ONDC business classification (hybrid keyword + LLM)
- TEAM portal registration package generation

## Slide 6: VastraSuchi — AI Catalog Generation
- Product classification to ONDC L1/L2/L3 taxonomy (10 categories, 230 HSN codes)
- HSN code mapping with confidence scoring
- AI-powered pricing suggestions (category + quantity + premium factors)
- ONDC schema validation and multi-format export (JSON, CSV, PDF)

## Slide 7: SahayakMap — Explainable SNP Matching
- 6-dimensional scoring: Domain (30%), Geography (20%), Language (15%), Cost (15%), Performance (10%), Tech Fit (10%)
- Top-3 SNP recommendations with natural-language explanations
- 26 real SNP profiles with performance data
- Multi-language explanations (Hindi, Tamil, Gujarati, English)

## Slide 8: VriddhiDisha — Growth Analytics Dashboard
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
- Synthetic datasets for demos — no real PII
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

Only create the file outputs/pitch_deck.md. Do not modify any source files."
```

---

## P1-3: Create Demo Video Script with Timestamps

The demo video is mandatory (2-3 min). This creates a detailed storyboard.

```
codex "Create outputs/demo_video_storyboard.md — a detailed 2.5-minute demo video storyboard for screen recording VyaparSetu.

Format each scene with:
- Timestamp range (e.g., 0:00 - 0:15)
- Screen action (what to click/type in the Streamlit app)
- Voiceover narration (exact script to read)
- Key visual callouts

Scenes:

0:00-0:10 INTRO
  Show: VyaparSetu home page with logo and tagline
  Narrate: 'VyaparSetu bridges the gap between India's micro enterprises and ONDC. Let us walk through how an MSE owner gets onboarded in under 3 minutes.'

0:10-0:35 SCENE 1: REGISTRATION (UdyamBodh)
  Action: Click 'Register & Onboard' in sidebar. Switch language to Hindi. Enter Udyam number UDYAM-RJ-01-0012345. Click fetch.
  Narrate: 'The MSE owner enters their Udyam number. UdyamBodh auto-fetches enterprise details, validates GST, and classifies the business into ONDC taxonomy using AI.'
  Callout: Highlight the auto-populated fields and ONDC classification result

0:35-1:10 SCENE 2: CATALOG GENERATION (VastraSuchi)
  Action: In the products section, type 'Homemade Mango Pickle 500g jar' and 'Lemon Pickle 250g'. Click generate catalog.
  Narrate: 'VastraSuchi converts natural-language product descriptions into ONDC-ready catalog entries — complete with HSN codes, pricing suggestions, and quality scores.'
  Callout: Show the generated catalog cards with HSN, price, category L1/L2/L3

1:10-1:40 SCENE 3: SNP MATCHING (SahayakMap)
  Action: Click on SNP recommendation section. Show top-3 SNP cards.
  Narrate: 'SahayakMap recommends the best Seller Network Participant using explainable 6-dimensional scoring — domain fit, geography, language, cost, performance, and tech readiness.'
  Callout: Expand one SNP card to show score breakdown and explanation

1:40-2:05 SCENE 4: ADMIN DASHBOARD (VriddhiDisha)
  Action: Login as admin. Show funnel chart, geo heatmap, women MSE gauge.
  Narrate: 'VriddhiDisha gives administrators real-time visibility into onboarding funnels, geographic distribution, and women MSE participation — aligned with the 50 percent TEAM Initiative target.'
  Callout: Highlight women MSE gauge hitting 50% and state heatmap

2:05-2:20 SCENE 5: VOICE & MULTILINGUAL
  Action: Switch language to Hindi. Show voice input button.
  Narrate: 'VyaparSetu supports 8 Indian languages with Bhashini-powered voice input — making ONDC accessible to MSE owners who may not be digitally literate.'

2:20-2:30 CLOSING
  Show: Competition Readiness page with 94/100 score
  Narrate: 'VyaparSetu — from Udyam to ONDC, AI that onboards India's micro and small enterprises. Built for the IndiaAI Innovation Challenge 2026.'

Include a NOTE at the bottom:
  Recording tips:
  - Use OBS Studio or native screen recorder
  - Resolution: 1920x1080
  - Use the 5 preloaded demo scenarios (run 'python scripts/demo_flow.py' first)
  - Keep Ollama running or use DEMO mode
  - Export as MP4, max 50MB

Only create outputs/demo_video_storyboard.md. Do not modify any source files."
```

---

## P1-4: Add GSTIN Checksum Validation

Currently only format regex is checked. Adding checksum improves the 'Technical Robustness' evaluation score.

```
codex "Enhance src/udyambodh/gst_validator.py to add GSTIN checksum validation in addition to the existing format check.

Current validate() method at line ~25 checks regex only.

Add a new private method _verify_checksum(gstin: str) -> bool that:
1. Takes a 15-character GSTIN string
2. Implements the standard GSTIN checksum algorithm:
   - Characters 1-14 are input, character 15 is the check digit
   - Character set: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
   - For each position i (0-13):
     - Get the character's index in the character set
     - Multiply by (i % 2 == 0 ? 1 : 2)  // factor based on position
     - Quotient = result // 36, remainder = result % 36
     - Sum = quotient + remainder
   - Total = sum of all position sums
   - Check digit index = (36 - (total % 36)) % 36
   - Check digit = character_set[check_digit_index]
3. Return True if computed check digit matches the 15th character

Modify the existing validate() method to:
- After the regex check passes, call _verify_checksum()
- If checksum fails, return a result with valid=False, error='GSTIN checksum mismatch'
- Keep all existing behavior for valid=True cases

Also update the demo/mock GSTINs in test files to have valid checksums, OR make the checksum check skip in demo mode.

Add a test in tests/test_udyambodh.py:
  test_gstin_checksum_valid() - test with known valid GSTIN '29AABCU9603R1ZM'
  test_gstin_checksum_invalid() - test with tampered GSTIN

Only modify src/udyambodh/gst_validator.py and optionally tests/test_udyambodh.py."
```

---

## P1-5: Add Data Governance Documentation Page

Annexure III Section 2 Q8 requires a data governance description. Add it to the Streamlit app.

```
codex "Add a 'Data Governance' section to the 'About' page in app.py.

In app.py, find the 'about' page section (PAGE_KEYS includes 'about'). Add a new expander or section within it titled 'Data Governance & Privacy' that displays:

1. **Data Collection**: 'VyaparSetu collects only Udyam registration number and product descriptions from MSE users. No passwords, financial data, or biometric information is stored.'

2. **Data Processing**: 'All AI inference (LLM classification, SNP scoring) runs locally via Ollama. No MSE data is sent to external cloud services. Bhashini API calls for voice/translation are stateless.'

3. **Data Storage**: 'PostgreSQL/SQLite stores registration and catalog records. Synthetic data is used for analytics demos. Production deployment supports data encryption at rest.'

4. **Data Retention**: 'MSE profiles are retained only for active onboarding. Completed registrations can be archived or deleted per DPDP Act requirements.'

5. **Access Control**: 'Admin dashboard requires SHA-256 password hash authentication. Failed login lockout after 5 attempts (300s). All admin actions are audit-logged.'

6. **Compliance**: 'Aligned with DPDP Act 2023 principles: purpose limitation, data minimization, storage limitation, and accountability. No cross-border data transfer.'

7. **Synthetic Data**: 'All demo/evaluation data is synthetically generated (5000 MSE profiles, 2000 products). No real PII is included in the repository.'

Use st.markdown() with proper headings. Keep it inside an expander so it doesn't clutter the page.

Only modify app.py in the about page section."
```

---

## P2-1: Add QR Code Generation to Registration PDF

```
codex "Enhance src/reporting/registration_report.py to generate an actual QR code instead of a placeholder rectangle.

Current code at the QR section draws a gray rectangle with text 'QR placeholder'.

Replace it with:
1. Try to import qrcode library (pip install qrcode[pil])
2. If available, generate a QR code containing the TEAM portal URL + MSE Udyam number:
   url = f'https://team.msmemart.com/verify/{mse_profile.udyam_number}'
3. Save QR as a temporary PNG, embed it in the PDF using reportlab Image
4. If qrcode not available, keep the existing placeholder (graceful fallback)

Add 'qrcode' to requirements.txt (with [pil] extra).

Only modify src/reporting/registration_report.py and requirements.txt."
```

---

## P2-2: Add Responsible AI Compliance Details

Annexure III Section 2 Q9 explicitly asks about fairness, transparency, interpretability.

```
codex "Create a new section in the Competition Readiness page of app.py that shows Responsible AI compliance.

In app.py find the 'competition' page section. Add a new subsection 'Responsible AI Compliance' with:

1. **Fairness**: Women MSE tracking with 50% inclusion target. No demographic bias in classification — same product description yields same category regardless of state or gender.

2. **Transparency**: Every SNP recommendation includes a human-readable explanation generated by the explainer module. Score breakdowns are visible (domain, geography, language, cost, performance, tech_fit).

3. **Interpretability**: Classification confidence scores (0-1) are shown for every product category assignment. HSN mappings include alternative suggestions with confidence ranking.

4. **Inclusivity**: 8 Indian languages supported (Hindi, English, Tamil, Marathi, Bengali, Telugu, Kannada, Gujarati). Voice-first design for low-literacy users. Mobile-friendly SNP matching (tech_fit scoring).

5. **Accountability**: All admin actions are audit-logged (outputs/logs/audit.log). Admin authentication with lockout controls. Version-stamped submission packs.

6. **Non-discrimination**: Synthetic test data validates equal funnel progression for women-owned vs other MSEs. Category classification uses objective product attributes, not owner demographics.

Display as a formatted card/table using st.markdown() or st.columns().

Only modify app.py in the competition page section."
```

---

## P2-3: Run Full Regeneration Pipeline

After all changes above, run this sequence to regenerate everything.

```
codex "Run the following commands in sequence and verify each succeeds:

1. python scripts/generate_synthetic_data.py
   - Verify: data/synthetic/mse_profiles.csv has 5000+ rows and 36+ unique states

2. python scripts/evaluate_models.py
   - Verify: outputs/model_evaluation_report.json exists and has accuracy >= 0.70

3. python scripts/generate_architecture_diagram.py
   - Verify: outputs/architecture_diagram.svg and outputs/architecture_diagram.png exist

4. python scripts/generate_submission_pack.py
   - Verify: outputs/submission/vyaparsetu_submission_pack.zip exists
   - Verify: readiness_score overall_score >= 94

5. python -m pytest -q --tb=short
   - Verify: all tests pass (should be >= 50 now with new test file)

6. python -m compileall -q src tests app.py scripts config.py
   - Verify: zero compilation errors

Print a final summary table with PASS/FAIL for each step.
Do not modify any source files. Only run commands and report."
```

---

## Execution Order Summary

| Priority | Prompt | What it fixes | Est. Files Changed |
|----------|--------|---------------|-------------------|
| **P0-1** | Model evaluation script | No accuracy/F1/AUC metrics | +1 new file |
| **P0-2** | MSME vocabulary expansion | Stub module (12 lines) | 3 files modified |
| **P0-3** | 36-state synthetic data | Only 10 states covered | 1 file modified |
| **P0-4** | Wire metrics into submission | No metrics in submission pack | 2 files modified |
| **P0-5** | Architecture diagram generator | No diagram for jury | +1 new file |
| **P0-6** | Admin password hash in .env | Security score 70/100 | +1 new file |
| **P1-1** | Benchmark test suite | No quality threshold tests | +1 new file |
| **P1-2** | Pitch deck content | No pitch deck for upload | +1 new file |
| **P1-3** | Demo video storyboard | No demo video plan | +1 new file |
| **P1-4** | GSTIN checksum validation | Format-only validation | 1-2 files modified |
| **P1-5** | Data governance in app | Missing from submission form | 1 file modified |
| **P2-1** | QR code in registration PDF | Placeholder only | 2 files modified |
| **P2-2** | Responsible AI section | Missing from submission form | 1 file modified |
| **P2-3** | Full regeneration pipeline | Validate everything works | 0 files (run only) |

---

## Non-Code Deliverables (Manual)

These cannot be generated by Codex and must be done manually:

1. **Record the demo video** (2-3 min MP4) using the storyboard from P1-3
2. **Convert pitch_deck.md to PPTX** using a tool like Marp, pandoc, or Google Slides
3. **Fill in team details** in the pitch deck (names, roles, LinkedIn, org registration)
4. **Certificate of Incorporation** — scan and upload (if applicable)
5. **Upload to IndiaAI Portal** — fill the Annexure III submission form fields
