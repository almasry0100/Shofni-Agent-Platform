from __future__ import annotations

from enum import Enum
from typing import TypeAlias


class FailureClass(str, Enum):
    SETUP_FAILURE = "SETUP_FAILURE"
    UNSUPPORTED_FEATURE = "UNSUPPORTED_FEATURE"
    PROTOCOL_TRANSLATION_FAILURE = "PROTOCOL_TRANSLATION_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    MODEL_BEHAVIOR_FAILURE = "MODEL_BEHAVIOR_FAILURE"
    GATEWAY_FAILURE = "GATEWAY_FAILURE"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    CLIENT_FAILURE = "CLIENT_FAILURE"
    TOOL_SCHEMA_FAILURE = "TOOL_SCHEMA_FAILURE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    CONTINUATION_FAILURE = "CONTINUATION_FAILURE"
    STREAMING_FAILURE = "STREAMING_FAILURE"
    FALLBACK_FAILURE = "FALLBACK_FAILURE"
    DUPLICATE_SIDE_EFFECT_FAILURE = "DUPLICATE_SIDE_EFFECT_FAILURE"
    EVIDENCE_OBSERVABILITY_FAILURE = "EVIDENCE_OBSERVABILITY_FAILURE"
    AUTH_ERROR = "AUTH_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    BILLING_ERROR = "BILLING_ERROR"
    CHECKPOINT_ERROR = "CHECKPOINT_ERROR"
    WORKSPACE_ERROR = "WORKSPACE_ERROR"


class SecondaryFailureClass(str, Enum):
    CLIENT_ERROR = "CLIENT_ERROR"
    PROTOCOL_ADAPTER_ERROR = "PROTOCOL_ADAPTER_ERROR"
    SHOFNI_NORMALIZATION_ERROR = "SHOFNI_NORMALIZATION_ERROR"
    PROVIDER_ROUTE_ERROR = "PROVIDER_ROUTE_ERROR"
    PROVIDER_CAPABILITY_MISSING = "PROVIDER_CAPABILITY_MISSING"
    UPSTREAM_SOURCE_ERROR = "UPSTREAM_SOURCE_ERROR"
    STREAM_ERROR = "STREAM_ERROR"
    TOOL_CONTINUATION_ERROR = "TOOL_CONTINUATION_ERROR"
    DUPLICATE_SIDE_EFFECT = "DUPLICATE_SIDE_EFFECT"
    MODEL_BEHAVIOR = "MODEL_BEHAVIOR"


FailureTaxonomyClass: TypeAlias = FailureClass | SecondaryFailureClass


def parse_failure_class(value: str) -> FailureTaxonomyClass:
    if not isinstance(value, str):
        raise TypeError("failure class must be a string")
    try:
        return FailureClass(value)
    except ValueError:
        try:
            return SecondaryFailureClass(value)
        except ValueError as exc:
            raise ValueError(f"unknown failure class: {value}") from exc


def serialize_failure_class(value: FailureTaxonomyClass) -> str:
    if not isinstance(value, (FailureClass, SecondaryFailureClass)):
        raise TypeError("failure class must be a known taxonomy enum")
    return value.value
