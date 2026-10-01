from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from poc.contracts._serialization import JSONValue
from poc.evidence.redactor import redact_value
from poc.evidence.taxonomy import ResolutionClass


class ResolutionEvidenceError(ValueError):
    """Raised when a Resolution record violates its attribution contract."""


@dataclass(frozen=True)
class ResolutionRecord:
    """Sanitized result record for one Resolution gate or repetition."""

    result_status: ResolutionClass
    classification: ResolutionClass
    candidate_reached: bool
    provider_reached: bool
    client_reached: bool
    candidate: str | None = None
    provider: str | None = None
    client: str | None = None
    test_id: str | None = None
    repetition: int | None = None
    evidence_refs: tuple[str, ...] = ()
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, JSONValue]:
        if self.repetition is not None and self.repetition < 1:
            raise ResolutionEvidenceError("repetition must be positive")
        result: dict[str, JSONValue] = {
            "result_status": self.result_status.value,
            "classification": self.classification.value,
            "candidate_reached": self.candidate_reached,
            "provider_reached": self.provider_reached,
            "client_reached": self.client_reached,
            "candidate": self.candidate,
            "provider": self.provider,
            "client": self.client,
            "test_id": self.test_id,
            "repetition": self.repetition,
            "evidence_refs": list(self.evidence_refs),
        }
        overlap = result.keys() & self.details.keys()
        if overlap:
            raise ResolutionEvidenceError(
                "details override defined fields: " + ", ".join(sorted(overlap))
            )
        result.update(redact_value(dict(self.details)))
        validate_resolution_record(result)
        return result


def validate_resolution_record(value: Mapping[str, Any]) -> None:
    required = {
        "result_status",
        "classification",
        "candidate_reached",
        "provider_reached",
        "client_reached",
        "evidence_refs",
    }
    missing = sorted(required - value.keys())
    if missing:
        raise ResolutionEvidenceError("missing Resolution fields: " + ", ".join(missing))
    for key in ("candidate_reached", "provider_reached", "client_reached"):
        if not isinstance(value[key], bool):
            raise ResolutionEvidenceError(f"{key} must be boolean")
    for key in ("result_status", "classification"):
        try:
            ResolutionClass(value[key])
        except (TypeError, ValueError) as exc:
            raise ResolutionEvidenceError(f"unknown Resolution {key}: {value[key]}") from exc
    refs = value["evidence_refs"]
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ResolutionEvidenceError("evidence_refs must be a list of non-empty strings")
    if value["classification"] == ResolutionClass.EXTERNAL_PROVIDER_BLOCKED.value:
        if value["result_status"] != ResolutionClass.BLOCKED.value:
            raise ResolutionEvidenceError("external provider blocking must have BLOCKED status")
        if value["candidate_reached"]:
            raise ResolutionEvidenceError(
                "external provider blocking before candidate execution requires candidate_reached=false"
            )
    if value["result_status"] == ResolutionClass.PASS.value and value["classification"] not in {
        ResolutionClass.PASS.value,
        ResolutionClass.EQUIVALENT_FOR_CURRENT_REQUIREMENTS.value,
    }:
        raise ResolutionEvidenceError("PASS status requires PASS or equivalence classification")


def resolution_record(**kwargs: Any) -> dict[str, JSONValue]:
    """Build and validate a JSON-compatible Resolution record."""

    return ResolutionRecord(**kwargs).to_dict()
