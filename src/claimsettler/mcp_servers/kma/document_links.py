"""Claim -> policy -> product cross-document reference graph.

KMA stores every chunk with its linking IDs in metadata (unmasked,
format-validated by Compliance Agent before this point) so retrieval can be
scoped to a specific claim/policy/product family via metadata_filter,
independent of embedding similarity.
"""

from __future__ import annotations

from typing import Any


def build_link_metadata(
    *,
    document_type: str,
    claim_id: str | None = None,
    policy_id: str | None = None,
    product_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"document_type": document_type}
    if claim_id:
        metadata["claim_id"] = claim_id
    if policy_id:
        metadata["policy_id"] = policy_id
    if product_id:
        metadata["product_id"] = product_id
    if extra:
        metadata.update(extra)
    return metadata
