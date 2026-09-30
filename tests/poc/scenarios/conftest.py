from __future__ import annotations

import pytest

from poc.fixtures.network import outbound_network_blocked


@pytest.fixture(autouse=True)
def block_non_loopback_tcp_connections():
    with outbound_network_blocked() as guard:
        yield
        assert guard.blocked_attempts == 0
