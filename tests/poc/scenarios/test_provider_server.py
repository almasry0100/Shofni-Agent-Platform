from __future__ import annotations

import socket

import pytest

from poc.fixtures.network import NetworkIsolationError, outbound_network_blocked
from poc.fixtures.provider_server import LocalProviderServer, probe_local_provider
from poc.fixtures.scenarios import run_scenario


def test_provider_server_binds_to_loopback_serves_fixture_and_releases_port() -> None:
    result = probe_local_provider("provider-server-seed")

    assert result["result_status"] == "PASS"
    assert result["server"]["bind_address"] == "127.0.0.1"
    assert result["server"]["selected_port"] > 0
    assert result["server"]["fixture_version"]
    assert result["server"]["fixture_hash"].startswith("sha256:")
    assert result["server"]["startup_result"] == "STARTED"
    assert result["server"]["shutdown_result"] == "STOPPED"
    assert result["server_port_released"] is True
    assert result["normalized_response"]["tool_calls"] == []

    record = run_scenario("provider_server_smoke", "provider-server-seed")
    assert record["result_status"] == "PASS"
    assert record["decisions"][0]["local_only"] is True
    assert record["decisions"][0]["port_released"] is True


def test_provider_server_rejects_non_loopback_bind_address() -> None:
    with pytest.raises(ValueError, match="loopback"):
        LocalProviderServer("0.0.0.0")


def test_network_guard_blocks_outbound_tcp_and_allows_loopback() -> None:
    with outbound_network_blocked() as guard:
        with pytest.raises(NetworkIsolationError):
            socket.create_connection(("198.51.100.17", 80), timeout=0.1)
        with LocalProviderServer():
            pass
    assert guard.blocked_attempts == 1
    assert guard.local_connections == 0
