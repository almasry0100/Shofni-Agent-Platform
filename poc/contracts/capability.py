from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable
from collections.abc import Mapping

from poc.evidence.schema import ProvenanceReference


class CapabilityState(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIAL = "PARTIAL"
    BROKEN = "BROKEN"
    EMULATED = "EMULATED"
    UNVERIFIED = "UNVERIFIED"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class CapabilityObservation:
    capability: str
    observed_state: CapabilityState
    evidence_references: tuple[ProvenanceReference, ...] = ()


@dataclass(frozen=True)
class CapabilityProbeResult:
    declared_metadata: Mapping[str, CapabilityState]
    probed_state: Mapping[str, CapabilityState]
    observations: tuple[CapabilityObservation, ...]
    evidence_references: tuple[ProvenanceReference, ...] = ()


@runtime_checkable
class CapabilityProbe(Protocol):
    def declared_metadata(self) -> Mapping[str, CapabilityState]: ...

    def probe(self) -> CapabilityProbeResult: ...


@dataclass(frozen=True)
class CompatibilityReport:
    client: str
    client_version: str | None
    provider: str
    model: str
    protocol: str
    declared_state: Mapping[str, CapabilityState] = field(default_factory=dict)
    probed_state: Mapping[str, CapabilityState] = field(default_factory=dict)
    observed_state: Mapping[str, CapabilityState] = field(default_factory=dict)
    effective_state: Mapping[str, CapabilityState] = field(default_factory=dict)
    provenance_references: tuple[ProvenanceReference, ...] = ()
