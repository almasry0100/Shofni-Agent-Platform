from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol, runtime_checkable

from ._serialization import JSONMapping, JSONValue


@runtime_checkable
class ClientProtocolAdapter(Protocol):
    def decode_request(self, wire_request: JSONValue) -> JSONMapping: ...

    def encode_response(self, response: JSONMapping) -> JSONValue: ...

    def encode_stream(self, events: Iterable[JSONValue]) -> Iterator[JSONValue]: ...

    def validate_wire_event(self, event: JSONValue) -> bool: ...
