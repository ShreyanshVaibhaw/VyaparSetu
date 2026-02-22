"""Central prompt templates for VyaparSetu LLM workflows."""

SYSTEM_PROMPT_VYAPARSETU = """You are VyaparSetu, an AI assistant helping Indian Micro and Small Enterprises get onto ONDC (Open Network for Digital Commerce). You help MSEs create professional product catalogs, understand e-commerce, and grow their business online.

CRITICAL RULES:
- Always be respectful and encouraging - these MSEs may be first-time digital sellers
- Generate product descriptions that are accurate, SEO-friendly, and ONDC-compliant
- Never exaggerate product claims - no "best in India" or unverifiable quality claims
- Classify products into correct ONDC taxonomy categories
- Support mixed Hindi-English input naturally
- Provide HSN codes accurately - incorrect codes cause GST compliance issues
- Keep language simple and accessible"""

PRODUCT_CATALOG_TEMPLATE = """Generate a professional ONDC product catalog entry for this MSE product.

MSE BUSINESS: {business_name} ({nic_description})
LOCATION: {district}, {state}
PRODUCT DESCRIPTION (as told by MSE): {raw_description}
LANGUAGE: {language}
CATEGORY HINT: {category_hint}

AVAILABLE ONDC CATEGORIES (pick the best match):
{categories_subset}

Generate ONLY this JSON:
{{
  "product_name_en": "concise English product name (max 80 chars)",
  "product_name_regional": "product name in {language} script",
  "short_description": "one-line description max 200 chars, include key selling points",
  "long_description": "detailed 150-200 word description. Include: what the product is, key features, materials/ingredients, usage, what makes it special. Write in professional e-commerce tone. NO fake claims.",
  "category_l1": "ONDC Level 1 category from the list",
  "category_l2": "ONDC Level 2 from the list",
  "category_l3": "ONDC Level 3 from the list or null",
  "hsn_code": "correct HSN code for this product",
  "suggested_price_range": "realistic price range in INR",
  "attributes": {{key product attributes like size, weight, material, color}},
  "tags": {{relevant tags: veg_nonveg, organic, handmade, etc.}},
  "seo_keywords": ["5-8 search keywords for ONDC discovery"]
}}

IMPORTANT:
- If MSE said "aam ka achaar, 500 gram, ghar ka bana hua": product_name_en = "Homemade Mango Pickle (500g)", category = Food & Beverage > Packaged Foods > Pickles & Chutneys
- If MSE said "cotton saree, Chanderi style": category = Fashion > Women's Apparel > Saree
- HSN code must be accurate - verify against the product type
- Price range should be realistic for the product type and segment"""

BUSINESS_CLASSIFICATION_TEMPLATE = """Classify this MSE's business into ONDC product categories.

BUSINESS DETAILS:
- Enterprise name: {enterprise_name}
- NIC code: {nic_code} ({nic_description})
- Declared products/services: {products_services}
- Location: {district}, {state}
- Activity type: {major_activity}

AVAILABLE ONDC CATEGORIES:
{ondc_categories}

Return ONLY this JSON:
{{
  "primary_category_l1": "most relevant ONDC L1 category",
  "primary_category_l2": "most relevant L2",
  "secondary_categories": ["other relevant L1 categories if applicable"],
  "suggested_product_types": ["specific product types this MSE likely sells based on NIC code and description"],
  "confidence": 0.0 to 1.0,
  "reasoning": "one line explaining the classification"
}}"""

SNP_EXPLANATION_TEMPLATE = """Generate a simple, friendly explanation for why this SNP is recommended for this MSE.

MSE: {mse_name} in {district}, {state}. Sells: {products}. Language: {language}.
SNP: {snp_name}. Specializes in: {snp_specialization}. Covers: {snp_coverage}. Commission: {commission}%.

MATCH SCORES:
- Domain fit: {domain_score}/1.0
- Geographic coverage: {geo_score}/1.0
- Language support: {lang_score}/1.0
- Cost: {cost_score}/1.0
- Performance: {perf_score}/1.0

Generate:
{{
  "explanation": "2-3 sentence explanation in simple language why this SNP is good for this MSE",
  "explanation_regional": "same explanation in {language}",
  "pros": ["3 key advantages"],
  "cons": ["1-2 honest limitations"],
  "tip": "one practical tip for the MSE when working with this SNP"
}}"""

CONVERSATIONAL_FORM_TEMPLATE = """You are helping an MSE fill their ONDC registration through conversation. Extract registration data from what they say.

CONVERSATION SO FAR:
{conversation_history}

MSE JUST SAID: "{latest_message}"

Extract any new information and return ONLY this JSON:
{{
  "extracted_fields": {{
    "udyam_number": "if mentioned, else null",
    "products": ["any products mentioned"],
    "price_info": "any pricing mentioned",
    "delivery_area": "any delivery area mentioned",
    "language_preference": "detected language",
    "other_info": "any other relevant info"
  }},
  "next_question": "the next question to ask the MSE to complete their registration (in {language})",
  "registration_complete": false
}}"""

PROMPT_TEMPLATES = {
    "system": SYSTEM_PROMPT_VYAPARSETU,
    "product_catalog": PRODUCT_CATALOG_TEMPLATE,
    "business_classification": BUSINESS_CLASSIFICATION_TEMPLATE,
    "snp_explanation": SNP_EXPLANATION_TEMPLATE,
    "conversational_form": CONVERSATIONAL_FORM_TEMPLATE,
}


def get_template(name: str) -> str:
    """Fetch a named template with graceful fallback."""
    return PROMPT_TEMPLATES.get(name, "{input}")
