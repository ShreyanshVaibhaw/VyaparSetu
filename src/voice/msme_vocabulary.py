"""MSME vocabulary normalization placeholders."""


def normalize_transcript(text: str, synonyms: dict[str, list[str]] | None = None) -> str:
    """Normalize common MSME terms in transcripts."""
    if not synonyms:
        return text
    normalized = text
    for canonical, variants in synonyms.items():
        for variant in variants:
            normalized = normalized.replace(variant, canonical)
    return normalized
