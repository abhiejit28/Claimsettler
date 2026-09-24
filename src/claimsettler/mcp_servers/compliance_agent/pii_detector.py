"""NER-based PII detection/masking. Presidio is the concrete Phase 1
implementation behind this interface (open-source, self-hosted via spaCy,
no API key) — swappable for a commercial tool (e.g. Protecto) later without
touching masking_policy.py or the MCP server that calls this."""

from __future__ import annotations

import hashlib
import re
from typing import ClassVar, Protocol


class PIIDetector(Protocol):
    def mask_free_text(self, text: str) -> str: ...


class PresidioPIIDetector:
    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine

        # Presidio's default nlp config pulls en_core_web_lg (~560MB); pin it
        # to the small model explicitly so Phase 1 stays lightweight and
        # doesn't trigger a large, unexpected download.
        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": spacy_model}],
            }
        ).create_engine()
        self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        self._anonymizer = AnonymizerEngine()

    def mask_free_text(self, text: str) -> str:
        if not text:
            return text
        results = self._analyzer.analyze(text=text, language="en")
        anonymized = self._anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text


class RegexOnlyPIIDetector:
    """Fallback: pattern-based detection only (SSN/phone/email/credit-card
    shapes). Faster, no model download, but misses free-text names/addresses
    that NER would catch — see docs/architecturePlan.md domain risks."""

    _PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "PHONE": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
        "CREDIT_CARD": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    }

    def mask_free_text(self, text: str) -> str:
        masked = text
        for label, pattern in self._PATTERNS.items():
            masked = pattern.sub(f"<{label}>", masked)
        return masked


def reversible_token(value: str, salt: str = "claimsettler-tokenize") -> str:
    """Consistent, reversible-by-lookup pseudonymization for TOKENIZED fields
    (e.g. VIN). Phase 1: deterministic HMAC-style digest kept short enough to
    stay readable in logs; a real reversible mapping table can replace this
    without changing callers, since they only depend on this function."""
    digest = hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]
    return f"TOK_{digest}"


def build_pii_detector(kind: str) -> PIIDetector:
    if kind == "presidio":
        return PresidioPIIDetector()
    return RegexOnlyPIIDetector()
