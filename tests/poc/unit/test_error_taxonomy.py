from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from poc.evidence.taxonomy import (
    FailureClass,
    SecondaryFailureClass,
    parse_failure_class,
    serialize_failure_class,
)


ROOT = Path(__file__).resolve().parents[3]
PRIMARY_FAILURES = {
    "SETUP_FAILURE",
    "UNSUPPORTED_FEATURE",
    "PROTOCOL_TRANSLATION_FAILURE",
    "PROVIDER_FAILURE",
    "MODEL_BEHAVIOR_FAILURE",
    "GATEWAY_FAILURE",
    "RUNTIME_FAILURE",
    "CLIENT_FAILURE",
    "TOOL_SCHEMA_FAILURE",
    "MALFORMED_RESPONSE",
    "CONTINUATION_FAILURE",
    "STREAMING_FAILURE",
    "FALLBACK_FAILURE",
    "DUPLICATE_SIDE_EFFECT_FAILURE",
    "EVIDENCE_OBSERVABILITY_FAILURE",
    "AUTH_ERROR",
    "RATE_LIMIT",
    "BILLING_ERROR",
    "CHECKPOINT_ERROR",
    "WORKSPACE_ERROR",
}
SECONDARY_FAILURES = {
    "CLIENT_ERROR",
    "PROTOCOL_ADAPTER_ERROR",
    "SHOFNI_NORMALIZATION_ERROR",
    "PROVIDER_ROUTE_ERROR",
    "PROVIDER_CAPABILITY_MISSING",
    "UPSTREAM_SOURCE_ERROR",
    "STREAM_ERROR",
    "TOOL_CONTINUATION_ERROR",
    "DUPLICATE_SIDE_EFFECT",
}


def test_every_authoritative_primary_failure_class_exists() -> None:
    assert {item.value for item in FailureClass} == PRIMARY_FAILURES


def test_primary_and_secondary_failure_serialization_is_stable() -> None:
    for failure in (*FailureClass, *SecondaryFailureClass):
        encoded = json.dumps({"failure_class": serialize_failure_class(failure)}, sort_keys=True)
        decoded = json.loads(encoded)["failure_class"]
        assert decoded == failure.value
        assert parse_failure_class(decoded) is failure
    assert {item.value for item in SecondaryFailureClass} >= SECONDARY_FAILURES


def test_unknown_or_invalid_values_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="unknown failure class"):
        parse_failure_class("SILENTLY_REMAP_ME")
    with pytest.raises(TypeError):
        parse_failure_class(None)
    with pytest.raises(TypeError):
        serialize_failure_class("PROVIDER_FAILURE")


def test_taxonomy_module_has_no_candidate_imports() -> None:
    source = ROOT / "poc/evidence/taxonomy.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {alias.name.split(".", 1)[0].casefold() for alias in node.names} & {
                "bifrost", "litellm", "openhands", "mastra"
            }
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0].casefold() not in {
                "bifrost", "litellm", "openhands", "mastra"
            }
