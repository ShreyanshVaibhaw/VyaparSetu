"""Shared Pydantic models for VyaparSetu."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class MSEProfile(BaseModel):
    """Micro/Small Enterprise profile from Udyam registration."""

    udyam_number: str
    enterprise_name: str
    owner_name: str
    owner_gender: Literal["Male", "Female", "Other"]
    enterprise_type: Literal["Micro", "Small"]
    major_activity: Literal["Manufacturing", "Services", "Trading"]
    nic_2digit: str
    nic_5digit: str
    nic_description: str
    state: str
    district: str
    pincode: str
    address: str
    mobile: Optional[str]
    email: Optional[str]
    date_of_incorporation: Optional[str]
    date_of_udyam: Optional[str]
    investment_plant: Optional[float]
    turnover: Optional[float]
    gstin: Optional[str]
    pan: Optional[str]
    social_category: Optional[str]
    is_women_owned: bool
    language_preference: str
    products_services: List[str]


class ONDCCatalogItem(BaseModel):
    """ONDC-compatible product catalog entry."""

    item_id: str
    mse_udyam: str
    product_name_en: str
    product_name_regional: Optional[str]
    short_description: str
    long_description: str
    category_l1: str
    category_l2: str
    category_l3: Optional[str]
    hsn_code: str
    price_mrp: float
    price_selling: float
    quantity_unit: str
    quantity_value: float
    images: List[str]
    attributes: Dict[str, str]
    tags: Dict[str, str]
    origin_country: str
    returnable: bool
    cancellable: bool
    available_on_cod: bool
    time_to_ship: str
    generated_by_ai: bool
    reviewed_by_mse: bool
    created_at: datetime


class SNPProfile(BaseModel):
    """Seller Network Participant profile on ONDC."""

    snp_id: str
    name: str
    website: Optional[str]
    supported_categories: List[str]
    geographic_coverage: List[str]
    pincode_coverage: Optional[List[str]]
    languages_supported: List[str]
    commission_rate: float
    onboarding_fee: float
    monthly_fee: float
    logistics_integrated: bool
    logistics_partners: List[str]
    payment_methods: List[str]
    platform_type: Literal["web", "mobile", "both"]
    catalog_upload_method: List[str]
    seller_support: List[str]
    avg_activation_days: int
    active_sellers: int
    seller_success_rate: float
    rating: float
    team_initiative_partner: bool
    specialization_tags: List[str]


class SNPMatch(BaseModel):
    """Result of MSE-SNP matching."""

    match_id: str
    mse_udyam: str
    snp_id: str
    snp_name: str
    overall_score: float
    domain_score: float
    geography_score: float
    language_score: float
    cost_score: float
    performance_score: float
    tech_fit_score: float
    explanation: str
    pros: List[str]
    cons: List[str]
    rank: int
    generated_at: datetime


class TEAMRegistration(BaseModel):
    """TEAM portal registration package."""

    registration_id: str
    mse_udyam: str
    mse_profile: MSEProfile
    product_categories: List[str]
    transaction_type: Literal["B2B", "B2C", "Both"]
    preferred_snp_id: Optional[str]
    catalog_items: List[ONDCCatalogItem]
    consent_given: bool
    language: str
    registration_status: Literal["Draft", "Submitted", "SNP_Assigned", "Live", "Active"]
    created_at: datetime
    submitted_at: Optional[datetime]


class OnboardingEvent(BaseModel):
    """Tracking event in onboarding funnel."""

    event_id: str
    mse_udyam: str
    stage: Literal["Registered", "Catalog_Created", "SNP_Matched", "Live", "First_Order"]
    timestamp: datetime
    district: str
    state: str
    category: str
    is_women_owned: bool
    snp_id: Optional[str]
    metadata: Dict[str, Any]


class ProductGenerationRequest(BaseModel):
    """Request to generate product catalog entry."""

    mse_udyam: str
    product_description_raw: str
    product_images: List[str]
    language: str
    category_hint: Optional[str]


class ConversationState(BaseModel):
    """State of voice/chat conversation with MSE."""

    session_id: str
    mse_udyam: Optional[str]
    current_step: str
    language: str
    collected_data: Dict[str, Any]
    history: List[Dict[str, str]]
