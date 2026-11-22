from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileInventory:
    path: str
    file_type: str
    size_bytes: int


@dataclass(frozen=True)
class RepositoryStructure:
    root_files: list[str] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    documentation_files: list[str] = field(default_factory=list)
    configuration_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TechnologyProfile:
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BuildTestProfile:
    build_commands: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    package_manifests: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SubmissionProfile:
    submission_id: str
    root_path: Path
    repository_structure: RepositoryStructure
    technology: TechnologyProfile
    build_test: BuildTestProfile
    documentation_files: list[str] = field(default_factory=list)
    total_files: int = 0
    risks: list[str] = field(default_factory=list)