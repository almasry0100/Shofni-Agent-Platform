from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ResolutionManifestError(ValueError):
    pass


REQUIRED_TOP_LEVEL = {
    "schema_version",
    "run_id",
    "resolution_plan_sha256",
    "resolution_plan_tracking_state",
    "starting_repository",
    "candidate_identities",
    "phases",
    "decision",
    "cleanup",
    "commit",
    "push",
}


def validate_resolution_manifest(value: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL - value.keys())
    if missing:
        raise ResolutionManifestError("missing manifest fields: " + ", ".join(missing))
    if not isinstance(value["run_id"], str) or not value["run_id"].startswith("resolution-"):
        raise ResolutionManifestError("run_id must use the resolution- prefix")
    digest = value["resolution_plan_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
        raise ResolutionManifestError("resolution_plan_sha256 must be a SHA-256 hex digest")
    if value["resolution_plan_tracking_state"] not in {"TRACKED", "UNTRACKED"}:
        raise ResolutionManifestError("resolution plan tracking state is invalid")
    repository = value["starting_repository"]
    if not isinstance(repository, Mapping) or not repository.get("branch") or not repository.get("head"):
        raise ResolutionManifestError("starting_repository must include branch and head")
    candidates = value["candidate_identities"]
    if not isinstance(candidates, list) or {item.get("candidate") for item in candidates if isinstance(item, Mapping)} != {
        "Bifrost",
        "LiteLLM",
        "OpenHands",
        "Mastra",
    }:
        raise ResolutionManifestError("candidate_identities must cover all four locked candidates")
    phases = value["phases"]
    if not isinstance(phases, Mapping) or set(phases) != {f"R{i}" for i in range(10)}:
        raise ResolutionManifestError("phases must contain R0 through R9")
    if value["commit"] is not False or value["push"] is not False:
        raise ResolutionManifestError("Resolution runs must not commit or push")
