from pathlib import Path

from app.profiling.submission_profiler import SubmissionProfiler


STARTER_PACK = (
    Path(__file__).resolve().parents[2]
    / "starter-pack"
)


def get_submission_path(
    challenge_id: str,
    submission_id: str,
) -> Path:
    return (
        STARTER_PACK
        / "challenges"
        / challenge_id
        / "submissions"
        / submission_id
    )


def test_profiles_deal_scoping_submission_001():
    profiler = SubmissionProfiler()

    submission_path = get_submission_path(
        "AI_DEAL_SCOPING_ASSISTANT",
        "SUB_001",
    )

    profile = profiler.profile(
        "SUB_001",
        submission_path,
    )

    assert profile.submission_id == "SUB_001"
    assert profile.total_files > 0

    assert "TypeScript" in profile.technology.languages
    assert "React" in profile.technology.frameworks

    assert any(
        "package.json" in path
        for path in profile.build_test.package_manifests
    )

    assert any(
        "build" in command
        for command in profile.build_test.build_commands
    )

    assert any(
        "test" in command
        for command in profile.build_test.test_commands
    )


def test_profiles_deal_scoping_submission_002():
    profiler = SubmissionProfiler()

    submission_path = get_submission_path(
        "AI_DEAL_SCOPING_ASSISTANT",
        "SUB_002",
    )

    profile = profiler.profile(
        "SUB_002",
        submission_path,
    )

    assert profile.submission_id == "SUB_002"
    assert profile.total_files > 0

    assert "TypeScript" in profile.technology.languages
    assert "React" in profile.technology.frameworks

    assert any(
        "/src/" in f"/{path}"
        for path in profile.repository_structure.source_files
    )

    assert any(
        "/docs/" in f"/{path}"
        for path in profile.repository_structure.documentation_files
    )

    assert any(
        "verify" in command or "build" in command
        for command in profile.build_test.build_commands
    )


def test_profiler_handles_nested_application_structure():
    profiler = SubmissionProfiler()

    submission_path = get_submission_path(
        "AI_DEAL_SCOPING_ASSISTANT",
        "SUB_001",
    )

    profile = profiler.profile(
        "SUB_001",
        submission_path,
    )

    assert any(
        path.startswith("deal-scoping-assistant/frontend/")
        for path in profile.repository_structure.source_files
    )