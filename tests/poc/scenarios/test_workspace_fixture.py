from __future__ import annotations

from pathlib import Path

import pytest

from poc.fixtures.scenarios import run_scenario
from poc.fixtures.workspace import DisposableWorkspace, WorkspaceError


def test_disposable_workspace_has_deterministic_contents_and_is_removed() -> None:
    workspace = DisposableWorkspace("workspace-seed")
    with workspace as active:
        root = active.root
        assert (root / "input" / "alpha.txt").read_text(encoding="utf-8") == "alpha fixture input\n"
        assert active.read_json("input/beta.json") == {"count": 2, "label": "beta"}
        assert (root / "output").is_dir()
        assert (root / "state").is_dir()
    assert not root.exists()


@pytest.mark.parametrize(
    "path",
    [
        "../escape.txt",
        "..\\escape.txt",
        "input/../../escape.txt",
        "C:\\Users\\outside\\secret.txt",
        "/tmp/outside.txt",
        "input/alpha.txt:stream",
    ],
)
def test_disposable_workspace_rejects_absolute_and_traversal_paths(path: str) -> None:
    with DisposableWorkspace("workspace-traversal-seed") as workspace:
        with pytest.raises(WorkspaceError):
            workspace.resolve_path(path)


def test_workspace_scenario_records_containment_checks() -> None:
    record = run_scenario("workspace_fixture", "workspace-scenario-seed")

    assert record["result_status"] == "PASS"
    assert record["decisions"][0]["rejected_traversal_attempts"] == 4
    assert record["decisions"][0]["sentinel_outside_workspace_unchanged"] is True
    assert record["decisions"][0]["disposable_workspace_cleaned"] is True


def test_file_symlink_cannot_redirect_workspace_write_outside_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    with DisposableWorkspace("workspace-symlink-seed") as workspace:
        link = workspace.root / "output" / "redirect"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("directory symlinks are unavailable on this host")
        with pytest.raises(WorkspaceError):
            workspace.write_text("output/redirect/sentinel.txt", "escaped")
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
