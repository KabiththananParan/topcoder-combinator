import hashlib
import json
from pathlib import Path

import pytest

from app.ideation.pipeline import IdeationPipeline
from app.ingestion.starter_pack_scanner import StarterPackScanner
from app.workspace.writer import WorkspaceWriter


def test_ideation_workspace_is_deterministic_and_source_safe(tmp_path):
    starter_pack = Path("../starter-pack").resolve()
    inventory = next(
        item
        for item in StarterPackScanner(starter_pack).scan()
        if item.challenge_id == "AGENTIC_AI_COMMUNITY_ENABLEMENT_SDLC"
    )
    source = next(
        path
        for path in sorted(
            (inventory.root_path / "submissions" / "SUB_001").rglob("*")
        )
        if path.is_file()
    )
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = IdeationPipeline().plan(
        challenge_id=inventory.challenge_id,
        submissions_root=inventory.root_path / "submissions",
        submission_ids=inventory.submission_ids,
    )

    writer = WorkspaceWriter(tmp_path)
    writer.write_ideation(inventory=inventory, result=result)
    first = (
        tmp_path / inventory.challenge_id / "workspace-manifest.json"
    ).read_bytes()
    writer.write_ideation(inventory=inventory, result=result)
    second = (
        tmp_path / inventory.challenge_id / "workspace-manifest.json"
    ).read_bytes()

    assert first == second
    workspace = tmp_path / inventory.challenge_id
    for artifact in (
        "review-context-status.json",
        "active-review-context.json",
        "review-context-reconciliation.json",
        "source-location-map.json",
        "overview.md",
        "ideas.json",
        "contradictions.json",
        "verification.json",
        "provenance.json",
        "llm-usage.json",
    ):
        assert (workspace / artifact).exists()
    assert (workspace / "submissions" / "SUB_001").is_dir()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert json.loads(
        (workspace / "review-context-status.json").read_text()
    )["mode"] == "specification_derived"
    usage = json.loads((workspace / "llm-usage.json").read_text())
    assert usage["provider"] == "mock"
    assert usage["calls"] == 0
    assert usage["totalTokens"] is None


def test_workspace_writer_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        WorkspaceWriter(tmp_path)._challenge_root("../outside")


def test_workspace_writer_rejects_symlinked_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "target.txt"
    target.write_text("outside")
    (source / "linked.txt").symlink_to(target)

    with pytest.raises(ValueError, match="Symlink source"):
        WorkspaceWriter._copy_tree(source, tmp_path / "destination")
