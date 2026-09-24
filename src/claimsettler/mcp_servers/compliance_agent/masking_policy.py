"""Field-aware, schema-driven masking taxonomy.

Three modes, never a single blanket NER pass over the whole document:
- UNMASKED: structural linking IDs KMA needs for claim->policy->product
  references. Format-validated, never sent through NER.
- NER_MASKED: free-text narrative fields — the only fields NER runs against.
- TOKENIZED: sensitive but cross-claim-linkable fields (e.g. VIN) get a
  reversible, consistent token instead of being fully masked, so
  SimilarClaimAgent / Phase 3 fraud-graph analysis can still match on them.

Refine this list with legal/compliance before Phase 1 ships to production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class FieldMode(StrEnum):
    UNMASKED = "unmasked"
    NER_MASKED = "ner_masked"
    TOKENIZED = "tokenized"


@dataclass(frozen=True)
class MaskingPolicy:
    unmasked_fields: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"claim_id", "policy_id", "product_id", "adjuster_id", "incident_date", "status"}
        )
    )
    ner_masked_fields: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "customer_name",
                "narrative",
                "address",
                "phone",
                "email",
                "ssn",
                "date_of_birth",
                "drivers_license",
                "medical_notes",
                "witness_statement",
            }
        )
    )
    tokenized_fields: frozenset[str] = field(default_factory=lambda: frozenset({"vin", "repair_shop_id"}))

    # Format validation for unmasked structural IDs — never let a value that
    # doesn't match its expected shape pass through unmasked.
    id_format: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]{3,64}$")

    def mode_for(self, field_name: str) -> FieldMode:
        if field_name in self.unmasked_fields:
            return FieldMode.UNMASKED
        if field_name in self.tokenized_fields:
            return FieldMode.TOKENIZED
        # Default-safe: anything not explicitly allow-listed is NER-masked,
        # never passed through unmasked by omission.
        return FieldMode.NER_MASKED

    def validate_unmasked(self, field_name: str, value: str) -> bool:
        return bool(self.id_format.match(value))


DEFAULT_POLICY = MaskingPolicy()
