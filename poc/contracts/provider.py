from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Protocol, runtime_checkable

from ._serialization import JSONMapping, JSONValue
from .capability import CapabilityProbeResult, CapabilityState


@runtime_checkable
class ProviderAdapter(Protocol):
    def declared_capabilities(self) -> Mapping[str, CapabilityState]: ...

    def probe(self) -> CapabilityProbeResult: ...

    def invoke(self, request: JSONMapping) -> JSONMapping: ...

    def normalize_response(self, response: JSONValue) -> JSONMapping: ...

    def normalize_stream(self, events: Iterable[JSONValue]) -> Iterator[JSONValue]: ...
