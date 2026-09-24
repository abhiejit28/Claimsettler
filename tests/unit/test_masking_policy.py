from claimsettler.mcp_servers.compliance_agent.masking_policy import DEFAULT_POLICY, FieldMode
from claimsettler.mcp_servers.compliance_agent.pii_detector import (
    RegexOnlyPIIDetector,
    reversible_token,
)
from claimsettler.mcp_servers.compliance_agent.scanner import scan_and_mask


def test_structural_ids_pass_through_unmasked():
    assert DEFAULT_POLICY.mode_for("claim_id") is FieldMode.UNMASKED
    assert DEFAULT_POLICY.mode_for("policy_id") is FieldMode.UNMASKED


def test_free_text_defaults_to_ner_masked():
    assert DEFAULT_POLICY.mode_for("narrative") is FieldMode.NER_MASKED
    assert DEFAULT_POLICY.mode_for("some_unknown_field") is FieldMode.NER_MASKED


def test_vin_is_tokenized_not_masked():
    assert DEFAULT_POLICY.mode_for("vin") is FieldMode.TOKENIZED


def test_reversible_token_is_deterministic():
    assert reversible_token("1HGCM82633A004352") == reversible_token("1HGCM82633A004352")
    assert reversible_token("1HGCM82633A004352") != reversible_token("OTHERVIN123456789")


def test_invalid_unmasked_id_falls_back_to_masking():
    # A structural ID with an SSN-shaped substring shows the fallback engages
    # the same detector path as any NER-masked field, not that the ID passes
    # through unmasked.
    detector = RegexOnlyPIIDetector()
    doc = {"claim_id": "bad id 123-45-6789", "narrative": "text"}
    result = scan_and_mask(doc, detector)
    assert result["report"]["claim_id"] == "ner_masked_fallback_invalid_format"
    assert result["masked_document"]["claim_id"] != doc["claim_id"]


def test_regex_detector_masks_known_pii_shapes():
    detector = RegexOnlyPIIDetector()
    doc = {
        "claim_id": "CLM-001",
        "narrative": "Call me at 555-123-4567 or email a@b.com. SSN 123-45-6789.",
    }
    result = scan_and_mask(doc, detector)
    masked = result["masked_document"]["narrative"]
    assert "555-123-4567" not in masked
    assert "a@b.com" not in masked
    assert "123-45-6789" not in masked
