from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from poc.fixtures.ledger import LedgerFixture
from poc.fixtures.scenarios import run_scenario
from poc.fixtures.workspace import DisposableWorkspace


def test_ledger_insert_replay_lookup_distinct_operation_and_reopen() -> None:
    record = run_scenario("t11_ledger_primitive", "t11-ledger-seed")
    assert record["result_status"] == "PASS"
    assert record["decisions"][0]["first_insert_created_one_record"] is True
    assert record["decisions"][0]["same_operation_replay_suppressed"] is True
    assert record["decisions"][0]["reopen_replay_suppressed"] is True
    assert record["decisions"][0]["rows_after_reopen"] == 2


def test_ledger_concurrent_replays_create_one_logical_record() -> None:
    with DisposableWorkspace("ledger-concurrency-seed") as workspace:
        ledger = LedgerFixture(workspace)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(
                    lambda _: ledger.append_ledger("shared-operation", {"value": "stable"}),
                    range(32),
                )
            )
        assert sum(result.inserted for result in results) == 1
        assert sum(result.duplicate_suppressed for result in results) == 31
        assert ledger.count("shared-operation") == 1
        assert ledger.lookup("shared-operation").result == {"value": "stable"}
        ledger.close()


def test_ledger_replay_with_conflicting_value_preserves_original_result() -> None:
    with DisposableWorkspace("ledger-conflict-seed") as workspace, LedgerFixture(workspace) as ledger:
        first = ledger.append_ledger("shared-operation", {"value": "original"})
        replay = ledger.append_ledger("shared-operation", {"value": "different"})

        assert first.inserted is True
        assert replay.duplicate_suppressed is True
        assert replay.value_conflict is True
        assert replay.result == {"value": "original"}
        assert ledger.count("shared-operation") == 1
