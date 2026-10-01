from pathlib import Path

from poc.runners.resolution_composition import _mount, _path_for_docker


def test_windows_docker_mount_uses_explicit_type_source_target() -> None:
    mount = _mount(Path(r"C:\workspace with spaces\repo"), "/workspace", readonly=True)
    assert mount.startswith("type=bind,source=C:/workspace with spaces/repo,target=/workspace")
    assert mount.endswith(",readonly")


def test_resolution_composition_keeps_distinct_execution_owners() -> None:
    source = Path("poc/runners/resolution_composition.py").read_text(encoding="utf-8")
    assert '"tool_execution_backend": "CLIENT"' in source
    assert '"tool_execution_backend": "RUNTIME"' in source
    assert '"runtime_provider_key": "NOT_PRESENT"' in source
    assert '"direct_provider_bypass": False' in source
    assert '"gateway_local_tool_execution": False' in source


def test_docker_path_formatter_uses_forward_slashes() -> None:
    assert "\\" not in _path_for_docker(Path(r"C:\workspace\repo"))
