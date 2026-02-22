"""Conversation engine for guided onboarding dialogue."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from src.common.models import ConversationState
from src.llm.prompt_templates import (
    CONVERSATIONAL_FORM_TEMPLATE,
    SYSTEM_PROMPT_VYAPARSETU,
)


class ConversationEngine:
    """Manage multilingual onboarding conversation state."""

    UDYAM_PATTERN = re.compile(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", re.IGNORECASE)

    def __init__(self, llm_client: Any, registration_engine: Any, bhashini_client: Any) -> None:
        self.llm = llm_client
        self.reg = registration_engine
        self.bhashini = bhashini_client

    def start_session(self, language: str = "hi") -> ConversationState:
        """Start a new registration conversation and include greeting."""
        greeting = self.get_greeting(language)
        return ConversationState(
            session_id=uuid4().hex,
            mse_udyam=None,
            current_step="udyam_input",
            language=language,
            collected_data={"products": []},
            history=[{"role": "assistant", "content": greeting}],
        )

    def process_message(self, state: ConversationState, message: str) -> tuple[ConversationState, str]:
        """Process one conversational turn and return updated state and response."""
        state.history.append({"role": "user", "content": message})
        extracted = self._extract_fields(state, message)
        self._merge_extracted(state, extracted)

        response: str
        if state.current_step in {"greeting", "udyam_input"}:
            udyam = self._extract_udyam(message) or extracted.get("udyam_number")
            if udyam:
                state.mse_udyam = udyam
                state.collected_data["udyam_number"] = udyam
                state.current_step = "product_input"
                response = self._localized_text(
                    state.language,
                    "धन्यवाद। अब अपने प्रोडक्ट्स बताइए (जैसे: आम का अचार, पापड़)।",
                    "Thanks. Now tell me your products (for example: mango pickle, papad).",
                    "நன்றி. இப்போது உங்கள் தயாரிப்புகளை சொல்லுங்கள்.",
                )
            else:
                response = self._localized_text(
                    state.language,
                    "कृपया अपना Udyam नंबर बताइए (फॉर्मेट: UDYAM-XX-00-0000000)।",
                    "Please share your Udyam number in format UDYAM-XX-00-0000000.",
                    "UDYAM வடிவத்தில் உங்கள் எண்ணை வழங்கவும் (UDYAM-XX-00-0000000).",
                )
        elif state.current_step == "product_input":
            products = state.collected_data.get("products", [])
            if products:
                state.current_step = "category_input"
                response = self._localized_text(
                    state.language,
                    f"अच्छा। मैंने ये प्रोडक्ट नोट किए: {', '.join(products[:5])}. क्या आप मुख्य कैटेगरी बताना चाहेंगे?",
                    f"Great. I noted these products: {', '.join(products[:5])}. Do you want to specify a main category?",
                    f"சரி. இந்த தயாரிப்புகள் பதிவு செய்யப்பட்டன: {', '.join(products[:5])}. முதன்மை வகையை கூற விரும்புகிறீர்களா?",
                )
            else:
                response = self._localized_text(
                    state.language,
                    "कृपया अपने 2-3 प्रोडक्ट के नाम बताएं।",
                    "Please share names of 2-3 products you sell.",
                    "நீங்கள் விற்கும் 2-3 தயாரிப்புகளின் பெயரை சொல்லுங்கள்.",
                )
        elif state.current_step == "category_input":
            state.collected_data["category_hint"] = message.strip()
            state.current_step = "snp_selection"
            response = self._localized_text(
                state.language,
                "ठीक है। अब SNP चुनिए: 1) कम कमीशन 2) तेज ऑनबोर्डिंग 3) क्षेत्रीय भाषा सपोर्ट",
                "Okay. Now pick SNP preference: 1) low commission 2) fast onboarding 3) regional language support",
                "சரி. SNP விருப்பத்தை தேர்வு செய்யவும்: 1) குறைந்த கமிஷன் 2) வேகமான onboarding 3) உள்ளூர் மொழி ஆதரவு",
            )
        elif state.current_step == "snp_selection":
            state.collected_data["snp_preference"] = self._parse_snp_choice(message)
            registration_id = ""
            status = "Draft"
            if state.mse_udyam:
                try:
                    registration = self.reg.auto_register(state.mse_udyam, language=state.language)
                    registration_id = registration.registration_id
                    status = registration.registration_status
                except Exception:
                    status = "Draft"
            state.collected_data["registration_id"] = registration_id
            state.collected_data["registration_status"] = status
            state.current_step = "confirmation"
            response = self._localized_text(
                state.language,
                f"पंजीकरण तैयार है। स्टेटस: {status}. ID: {registration_id or 'N/A'}. क्या आगे SNP मैपिंग शुरू करें?",
                f"Registration package is ready. Status: {status}. ID: {registration_id or 'N/A'}. Shall we continue to SNP mapping?",
                f"பதிவு தயாராகியுள்ளது. நிலை: {status}. ID: {registration_id or 'N/A'}. அடுத்ததாக SNP மேப்பிங்குக்கு செல்லலாமா?",
            )
        else:
            response = self._localized_text(
                state.language,
                "धन्यवाद। आपकी जानकारी सुरक्षित कर ली गई है।",
                "Thank you. Your information has been saved.",
                "நன்றி. உங்கள் தகவல் சேமிக்கப்பட்டது.",
            )

        state.history.append({"role": "assistant", "content": response})
        return state, response

    def get_greeting(self, language: str) -> str:
        """Return localized greeting."""
        greetings = {
            "hi": "नमस्ते! व्यापारसेतु में आपका स्वागत है। मैं आपकी दुकान को ONDC पर लाने में मदद करूँगा।",
            "en": "Welcome to VyaparSetu! I will help you bring your business to ONDC.",
            "ta": "வணக்கம்! VyaparSetu-க்கு வரவேற்கிறோம். உங்கள் வணிகத்தை ONDC-யில் கொண்டு வர உதவுவேன்.",
        }
        return greetings.get(language, greetings["en"])

    def _extract_fields(self, state: ConversationState, latest_message: str) -> dict[str, Any]:
        history_text = "\n".join(f"{h['role']}: {h['content']}" for h in state.history[-8:])
        prompt = CONVERSATIONAL_FORM_TEMPLATE.format(
            conversation_history=history_text,
            latest_message=latest_message,
            language=state.language,
        )
        try:
            data = self.llm.generate_json(prompt=prompt, system=SYSTEM_PROMPT_VYAPARSETU)
            return data.get("extracted_fields", {}) if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _merge_extracted(self, state: ConversationState, extracted: dict[str, Any]) -> None:
        if not isinstance(extracted, dict):
            return
        products = extracted.get("products", [])
        if isinstance(products, list):
            existing = list(state.collected_data.get("products", []))
            for product in products:
                if product and product not in existing:
                    existing.append(str(product))
            state.collected_data["products"] = existing

        for key in ["price_info", "delivery_area", "language_preference", "other_info", "udyam_number"]:
            value = extracted.get(key)
            if value:
                state.collected_data[key] = value
                if key == "udyam_number" and not state.mse_udyam:
                    state.mse_udyam = str(value)

        # Fallback local parsing when LLM did not extract products.
        if not state.collected_data.get("products"):
            inferred = self._extract_products_from_text(state.history[-1]["content"])
            if inferred:
                state.collected_data["products"] = inferred

    def _extract_udyam(self, text: str) -> str | None:
        match = self.UDYAM_PATTERN.search(text.upper())
        return match.group(0) if match else None

    def _extract_products_from_text(self, text: str) -> list[str]:
        cleaned = text.replace("और", ",").replace("and", ",")
        parts = [p.strip(" .") for p in cleaned.split(",") if p.strip()]
        return parts[:5]

    def _parse_snp_choice(self, message: str) -> str:
        lowered = message.lower()
        if "1" in lowered or "कम" in lowered or "low" in lowered:
            return "low_commission"
        if "2" in lowered or "fast" in lowered or "तेज" in lowered:
            return "fast_onboarding"
        if "3" in lowered or "language" in lowered or "भाषा" in lowered:
            return "language_support"
        return "balanced"

    def _localized_text(self, language: str, hi: str, en: str, ta: str) -> str:
        if language == "hi":
            return hi
        if language == "ta":
            return ta
        return en


def next_prompt(state: dict[str, Any], user_input: str) -> dict[str, Any]:
    """Backward-compatible helper used by early scaffold."""
    step = int(state.get("step", 0)) + 1
    return {
        "step": step,
        "last_user_input": user_input,
        "assistant_prompt": "Please share your next business detail.",
    }
