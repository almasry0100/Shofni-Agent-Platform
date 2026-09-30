from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from poc.evidence.taxonomy import FailureTaxonomyClass

from ._serialization import JSONMapping


@runtime_checkable
class GatewayBackend(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def request(self, request: JSONMapping) -> JSONMapping: ...

    def stream(self, request: JSONMapping) -> Iterator[JSONMapping]: ...

    def list_models(self) -> list[JSONMapping]: ...

    def classify_error(self, error: object) -> FailureTaxonomyClass: ...
