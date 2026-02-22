"""Bhashini speech/translation client with demo-safe mock mode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from config import BHASHINI_API_URL, BHASHINI_INFERENCE_URL
from src.common.logger import get_logger


logger = get_logger(__name__)


@dataclass
class TranscriptionResult:
    """Structured transcription output."""

    text: str
    language: str
    confidence: float = 0.0
    is_mock: bool = False
    message: str = ""


class MockBhashiniClient:
    """Offline fallback client that works without API keys."""

    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        return TranscriptionResult(
            text="यह डेमो ट्रांसक्रिप्शन है।",
            language=language,
            confidence=0.5,
            is_mock=True,
            message="Mock transcription used.",
        )

    def text_to_speech(self, text: str, language: str) -> bytes:
        return f"[{language}] {text}".encode("utf-8")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        return text


class BhashiniClient:
    """Bhashini integration with automatic mock fallback."""

    def __init__(
        self,
        api_url: str | None = None,
        inference_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.api_url = api_url or BHASHINI_API_URL
        self.inference_url = inference_url or BHASHINI_INFERENCE_URL
        self.api_key = api_key or os.getenv("BHASHINI_API_KEY", "")
        self.mock = MockBhashiniClient()

    @property
    def demo_mode(self) -> bool:
        return not bool(self.api_key)

    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        """Convert speech bytes to text."""
        if self.demo_mode:
            return self.mock.transcribe(audio_bytes, language)
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {"sourceLanguage": language}
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            response = requests.post(
                f"{self.inference_url}/asr",
                headers=headers,
                data=payload,
                files=files,
                timeout=20,
            )
            response.raise_for_status()
            body = response.json()
            text = str(body.get("text", "")).strip()
            conf = float(body.get("confidence", 0.0))
            return TranscriptionResult(text=text, language=language, confidence=conf, is_mock=False)
        except Exception as exc:
            result = self.mock.transcribe(audio_bytes, language)
            result.message = f"ASR fallback to mock: {exc}"
            return result

    def text_to_speech(self, text: str, language: str) -> bytes:
        """Convert text to speech bytes."""
        if self.demo_mode:
            return self.mock.text_to_speech(text, language)
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"text": text, "language": language}
            response = requests.post(f"{self.inference_url}/tts", json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            if response.content:
                return response.content
            return self.mock.text_to_speech(text, language)
        except Exception as exc:
            logger.warning("Bhashini TTS failed, using mock output: %s", exc)
            return self.mock.text_to_speech(text, language)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between supported languages."""
        if self.demo_mode:
            return self.mock.translate(text, source_lang, target_lang)
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"text": text, "sourceLanguage": source_lang, "targetLanguage": target_lang}
            response = requests.post(f"{self.inference_url}/translate", json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            body = response.json()
            translated = body.get("translatedText")
            if isinstance(translated, str) and translated:
                return translated
            return text
        except Exception as exc:
            logger.warning("Bhashini translation failed, returning source text: %s", exc)
            return text

    # Backward-compatible alias used in earlier scaffold.
    def synthesize(self, text: str, target_language: str = "hi") -> dict[str, str]:
        audio = self.text_to_speech(text, target_language)
        return {"text": text, "target_language": target_language, "audio_path": f"bytes:{len(audio)}"}
