from __future__ import annotations

import ipaddress
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator


class NetworkIsolationError(RuntimeError):
    pass


@dataclass
class NetworkGuard:
    blocked_attempts: int = 0
    local_connections: int = 0


def _is_loopback_host(host: object) -> bool:
    if not isinstance(host, str):
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


@contextmanager
def outbound_network_blocked() -> Iterator[NetworkGuard]:
    """Reject every TCP connection target except an IP loopback address."""

    guard = NetworkGuard()
    original_connect = socket.socket.connect
    original_create_connection = socket.create_connection

    def guarded_connect(sock: socket.socket, address: object) -> object:
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            guard.blocked_attempts += 1
            raise NetworkIsolationError("non-loopback TCP connection blocked")
        guard.local_connections += 1
        return original_connect(sock, address)

    def guarded_create_connection(address: object, *args: object, **kwargs: object) -> socket.socket:
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            guard.blocked_attempts += 1
            raise NetworkIsolationError("non-loopback TCP connection blocked")
        return original_create_connection(address, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.create_connection = guarded_create_connection
    try:
        yield guard
    finally:
        socket.socket.connect = original_connect
        socket.create_connection = original_create_connection
