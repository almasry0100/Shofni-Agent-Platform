from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from poc.contracts._serialization import JSONValue, timestamp_to_json
from .taxonomy import FailureTaxonomyClass, parse_failure_class, serialize_failure_class


class EvidenceSchemaError(ValueError):
    pass


class EvidenceType(str, Enum):
    LIVE_PROVIDER_EVIDENCE = "LIVE_PROVIDER_EVIDENCE"
    SYNTHETIC_FIXTURE_EVIDENCE = "SYNTHETIC_FIXTURE_EVIDENCE"
    SOURCE_INSPECTION_EVIDENCE = "SOURCE_INSPECTION_EVIDENCE"
    BASELINE_EVIDENCE = "BASELINE_EVIDENCE"


class BehaviorMode(str, Enum):
    NATIVE = "NATIVE"
    EMULATED = "EMULATED"
    REPAIRED = "REPAIRED"
    UNSUPPORTED = "UNSUPPORTED"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ResultStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"


def load_evidence_schema() -> dict[str, Any]:
    path = Path(__file__).with_name("schema.json")
    with path.open("r", encoding="utf-8") as stream:
        schema = json.load(stream)
    if not isinstance(schema, dict):
        raise EvidenceSchemaError("evidence schema must be a JSON object")
    return schema


def _matches_schema_type(value: object, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "null":
        return value is None
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise EvidenceSchemaError(f"unsupported schema type in schema.json: {expected}")


def _validate_schema_value(value: object, definition: Mapping[str, Any], path: str) -> None:
    allowed_types = definition.get("type")
    if isinstance(allowed_types, str):
        allowed_types = [allowed_types]
    if allowed_types and not any(_matches_schema_type(value, item) for item in allowed_types):
        raise EvidenceSchemaError(f"{path} does not match its schema type")
    if "minLength" in definition and isinstance(value, str) and len(value) < definition["minLength"]:
        raise EvidenceSchemaError(f"{path} is shorter than its schema minimum")
    if "enum" in definition and value not in definition["enum"]:
        raise EvidenceSchemaError(f"{path} is not an allowed schema value")
    if definition.get("format") == "date-time":
        if not isinstance(value, str):
            raise EvidenceSchemaError(f"{path} must be a date-time string")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EvidenceSchemaError(f"{path} must be an ISO date-time") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise EvidenceSchemaError(f"{path} must include a timezone")


def validate_evidence_envelope(value: Mapping[str, object]) -> None:
    schema = load_evidence_schema()
    if not isinstance(value, Mapping):
        raise EvidenceSchemaError("evidence envelope must be an object")
    properties = schema["properties"]
    for name in schema["required"]:
        if name not in value:
            raise EvidenceSchemaError(f"missing required evidence field: {name}")
    for name, item in value.items():
        definition = properties.get(name)
        if definition is None:
            if schema.get("additionalProperties") is False:
                raise EvidenceSchemaError(f"unexpected evidence field: {name}")
            continue
        _validate_schema_value(item, definition, name)
        if name == "provenance_references":
            nested = definition["items"]
            for index, reference in enumerate(item):
                if not isinstance(reference, Mapping):
                    raise EvidenceSchemaError(f"provenance_references[{index}] must be an object")
                for nested_name in nested["required"]:
                    if nested_name not in reference:
                        raise EvidenceSchemaError(
                            f"missing provenance field: provenance_references[{index}].{nested_name}"
                        )
                for nested_name, nested_value in reference.items():
                    nested_definition = nested["properties"].get(nested_name)
                    if nested_definition is None:
                        if nested.get("additionalProperties") is False:
                            raise EvidenceSchemaError(
                                f"unexpected provenance field: provenance_references[{index}].{nested_name}"
                            )
                        continue
                    _validate_schema_value(
                        nested_value,
                        nested_definition,
                        f"provenance_references[{index}].{nested_name}",
                    )


@dataclass(frozen=True)
class ProvenanceReference:
    reference_type: str
    reference: str | None
    digest: str | None
    candidate_tree_hash: str | None
    artifact_pin: str | None
    status: str | None

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "reference_type": self.reference_type,
            "reference": self.reference,
            "digest": self.digest,
            "candidate_tree_hash": self.candidate_tree_hash,
            "artifact_pin": self.artifact_pin,
            "status": self.status,
        }


@dataclass(frozen=True)
class EvidenceEnvelope:
    test_run_id: str
    timestamp_utc: datetime
    evidence_type: EvidenceType
    result_status: ResultStatus
    test_id: str | None
    candidate: str | None
    client: str | None
    client_version: str | None
    provider: str | None
    model_id: str | None
    protocol: str | None
    request_id: str | None
    task_id: str | None
    session_id: str | None
    attempt_id: str | None
    workspace_id: str | None
    checkpoint_id: str | None
    tool_call_id: str | None
    operation_id: str | None
    behavior_mode: BehaviorMode | None
    failure_class: FailureTaxonomyClass | None
    provenance_references: tuple[ProvenanceReference, ...]
    additional_properties: Mapping[str, JSONValue] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.test_run_id:
            raise ValueError("test_run_id must be a non-empty string")
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() is None:
            raise ValueError("timestamp_utc must include a timezone")
        object.__setattr__(self, "timestamp_utc", self.timestamp_utc.astimezone(timezone.utc))

    def to_dict(self) -> dict[str, JSONValue]:
        result: dict[str, JSONValue] = {
            "test_run_id": self.test_run_id,
            "test_id": self.test_id,
            "candidate": self.candidate,
            "client": self.client,
            "client_version": self.client_version,
            "provider": self.provider,
            "model_id": self.model_id,
            "protocol": self.protocol,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "attempt_id": self.attempt_id,
            "workspace_id": self.workspace_id,
            "checkpoint_id": self.checkpoint_id,
            "tool_call_id": self.tool_call_id,
            "operation_id": self.operation_id,
            "timestamp_utc": timestamp_to_json(self.timestamp_utc),
            "evidence_type": self.evidence_type.value,
            "behavior_mode": self.behavior_mode.value if self.behavior_mode else None,
            "result_status": self.result_status.value,
            "failure_class": serialize_failure_class(self.failure_class) if self.failure_class else None,
            "provenance_references": [reference.to_dict() for reference in self.provenance_references],
        }
        overlap = result.keys() & self.additional_properties.keys()
        if overlap:
            raise ValueError(f"additional evidence properties override defined fields: {', '.join(sorted(overlap))}")
        result.update(self.additional_properties)
        validate_evidence_envelope(result)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> EvidenceEnvelope:
        validate_evidence_envelope(value)
        known = set(load_evidence_schema()["properties"])
        references = tuple(
            ProvenanceReference(
                reference_type=item["reference_type"],
                reference=item["reference"],
                digest=item["digest"],
                candidate_tree_hash=item["candidate_tree_hash"],
                artifact_pin=item["artifact_pin"],
                status=item["status"],
            )
            for item in value["provenance_references"]
        )
        failure = value["failure_class"]
        mode = value["behavior_mode"]
        return cls(
            test_run_id=value["test_run_id"],
            timestamp_utc=datetime.fromisoformat(value["timestamp_utc"].replace("Z", "+00:00")),
            evidence_type=EvidenceType(value["evidence_type"]),
            result_status=ResultStatus(value["result_status"]),
            test_id=value["test_id"],
            candidate=value["candidate"],
            client=value["client"],
            client_version=value["client_version"],
            provider=value["provider"],
            model_id=value["model_id"],
            protocol=value["protocol"],
            request_id=value["request_id"],
            task_id=value["task_id"],
            session_id=value["session_id"],
            attempt_id=value["attempt_id"],
            workspace_id=value["workspace_id"],
            checkpoint_id=value["checkpoint_id"],
            tool_call_id=value["tool_call_id"],
            operation_id=value["operation_id"],
            behavior_mode=BehaviorMode(mode) if mode is not None else None,
            failure_class=parse_failure_class(failure) if failure is not None else None,
            provenance_references=references,
            additional_properties={key: item for key, item in value.items() if key not in known},
        )


def dumps_evidence_envelope(envelope: EvidenceEnvelope) -> str:
    return json.dumps(envelope.to_dict(), sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def loads_evidence_envelope(serialized: str) -> EvidenceEnvelope:
    value = json.loads(serialized)
    if not isinstance(value, dict):
        raise EvidenceSchemaError("evidence envelope JSON must contain an object")
    return EvidenceEnvelope.from_dict(value)
