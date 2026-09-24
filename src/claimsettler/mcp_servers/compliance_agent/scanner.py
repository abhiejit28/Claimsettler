from __future__ import annotations

from typing import Any

from .masking_policy import DEFAULT_POLICY, FieldMode, MaskingPolicy
from .pii_detector import PIIDetector, reversible_token


def scan_and_mask(
    document: dict[str, Any],
    detector: PIIDetector,
    policy: MaskingPolicy = DEFAULT_POLICY,
) -> dict[str, Any]:
    """Applies the field-aware masking taxonomy to a normalized claim document.

    Returns {"masked_document": {...}, "report": {field: mode, ...}} — the
    report lets callers/audit trail see exactly what was masked/tokenized
    without exposing the original values.
    """
    masked: dict[str, Any] = {}
    report: dict[str, str] = {}

    for field_name, value in document.items():
        if not isinstance(value, str):
            masked[field_name] = value
            continue

        mode = policy.mode_for(field_name)
        if mode is FieldMode.UNMASKED:
            if not policy.validate_unmasked(field_name, value):
                # Defense-in-depth: a structural ID that doesn't match its
                # expected format is NOT trusted unmasked — fall back to
                # NER masking rather than silently leaking an odd value.
                masked[field_name] = detector.mask_free_text(value)
                report[field_name] = "ner_masked_fallback_invalid_format"
            else:
                masked[field_name] = value
                report[field_name] = FieldMode.UNMASKED.value
        elif mode is FieldMode.TOKENIZED:
            masked[field_name] = reversible_token(value)
            report[field_name] = FieldMode.TOKENIZED.value
        else:
            masked[field_name] = detector.mask_free_text(value)
            report[field_name] = FieldMode.NER_MASKED.value

    return {"masked_document": masked, "report": report}
