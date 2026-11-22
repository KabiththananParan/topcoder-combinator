import json
from pathlib import Path

from .models import (
    BuildTestProfile,
    RepositoryStructure,
    SubmissionProfile,
    TechnologyProfile,
)


class SubmissionProfiler:
    SOURCE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".php",
        ".cs",
        ".rb",
    }

    TEST_MARKERS = (
        "test",
        "tests",
        "spec",
    )

    DOCUMENTATION_NAMES = {
        "README",
        "README.md",
        "README.txt",
        "README.rst",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
    }

    DOCUMENTATION_EXTENSIONS = {
        ".md",
        ".rst",
        ".txt",
    }

    DOCUMENTATION_DIRECTORIES = {
        "docs",
        "documentation",
    }

    CONFIGURATION_NAMES = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "vite.config.ts",
        "vite.config.js",
        "tsconfig.json",
    }

    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++",
        ".hpp": "C++",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".cs": "C#",
        ".rb": "Ruby",
    }

    FRAMEWORK_HINTS = {
        "react": "React",
        "vite": "Vite",
        "next": "Next.js",
        "fastapi": "FastAPI",
        "express": "Express",
        "flask": "Flask",
        "django": "Django",
        "vue": "Vue",
        "angular": "Angular",
    }

    PACKAGE_MANAGER_FILES = {
        "package.json": "npm",
        "package-lock.json": "npm",
        "pnpm-lock.yaml": "pnpm",
        "yarn.lock": "yarn",
        "requirements.txt": "pip",
        "pyproject.toml": "pip",
        "Pipfile": "pipenv",
    }

    def profile(
        self,
        submission_id: str,
        submission_path: Path,
    ) -> SubmissionProfile:
        submission_path = submission_path.resolve()

        if not submission_path.exists():
            raise ValueError(
                f"Submission does not exist: {submission_path}"
            )

        if not submission_path.is_dir():
            raise ValueError(
                f"Submission is not a directory: {submission_path}"
            )

        files = self._collect_files(submission_path)

        repository_structure = self._build_repository_structure(
            submission_path,
            files,
        )

        technology = self._build_technology_profile(
            submission_path,
            files,
        )

        build_test = self._build_test_profile(
            submission_path,
            files,
        )

        documentation_files = [
            self._relative_path(submission_path, path)
            for path in files
            if self._is_documentation_file(path)
        ]

        risks = self._detect_basic_risks(
            submission_path,
            files,
            build_test,
        )

        return SubmissionProfile(
            submission_id=submission_id,
            root_path=submission_path,
            repository_structure=repository_structure,
            technology=technology,
            build_test=build_test,
            documentation_files=sorted(
                set(documentation_files)
            ),
            total_files=len(files),
            risks=risks,
        )

    def _collect_files(self, root: Path) -> list[Path]:
        return sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and not self._should_ignore(path)
        )

    def _should_ignore(self, path: Path) -> bool:
        ignored_directories = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".next",
            "coverage",
        }

        return any(
            part in ignored_directories
            for part in path.parts
        )

    def _relative_path(
        self,
        root: Path,
        path: Path,
    ) -> str:
        return path.relative_to(root).as_posix()

    def _build_repository_structure(
        self,
        root: Path,
        files: list[Path],
    ) -> RepositoryStructure:
        root_files = []
        directories = set()
        source_files = []
        test_files = []
        documentation_files = []
        configuration_files = []

        for path in files:
            relative = self._relative_path(root, path)

            if len(Path(relative).parts) == 1:
                root_files.append(relative)

            directories.update(
                str(parent)
                for parent in path.relative_to(root).parents
                if str(parent) != "."
            )

            if path.suffix.lower() in self.SOURCE_EXTENSIONS:
                source_files.append(relative)

            if self._is_test_file(path):
                test_files.append(relative)

            if self._is_documentation_file(path):
                documentation_files.append(relative)

            if path.name in self.CONFIGURATION_NAMES:
                configuration_files.append(relative)

        return RepositoryStructure(
            root_files=sorted(root_files),
            directories=sorted(directories),
            source_files=sorted(source_files),
            test_files=sorted(test_files),
            documentation_files=sorted(documentation_files),
            configuration_files=sorted(configuration_files),
        )

    def _is_test_file(self, path: Path) -> bool:
        name = path.name.lower()

        if any(marker in name for marker in self.TEST_MARKERS):
            return True

        return any(
            marker in {part.lower() for part in path.parts}
            for marker in self.TEST_MARKERS
        )

    def _is_documentation_file(self, path: Path) -> bool:
        if path.name in self.DOCUMENTATION_NAMES:
            return True

        if path.suffix.lower() in self.DOCUMENTATION_EXTENSIONS:
            return True

        return any(
            part.lower() in self.DOCUMENTATION_DIRECTORIES
            for part in path.parts
        )

    def _build_technology_profile(
        self,
        root: Path,
        files: list[Path],
    ) -> TechnologyProfile:
        languages = set()
        frameworks = set()
        package_managers = set()
        databases = set()

        for path in files:
            language = self.LANGUAGE_MAP.get(
                path.suffix.lower()
            )

            if language:
                languages.add(language)

            package_manager = self.PACKAGE_MANAGER_FILES.get(
                path.name
            )

            if package_manager:
                package_managers.add(package_manager)

        for path in files:
            if path.name == "package.json":
                self._inspect_package_json(
                    path,
                    frameworks,
                    databases,
                )

        return TechnologyProfile(
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            package_managers=sorted(package_managers),
            databases=sorted(databases),
        )

    def _inspect_package_json(
        self,
        path: Path,
        frameworks: set[str],
        databases: set[str],
    ) -> None:
        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return

        dependencies = {}

        dependencies.update(
            data.get("dependencies", {})
        )

        dependencies.update(
            data.get("devDependencies", {})
        )

        dependency_names = {
            name.lower()
            for name in dependencies
        }

        for hint, framework in self.FRAMEWORK_HINTS.items():
            if any(
                hint in dependency
                for dependency in dependency_names
            ):
                frameworks.add(framework)

        database_hints = {
            "mongodb": "MongoDB",
            "mongoose": "MongoDB",
            "mysql": "MySQL",
            "pg": "PostgreSQL",
            "postgres": "PostgreSQL",
            "prisma": "Prisma",
            "sequelize": "SQL database",
        }

        for hint, database in database_hints.items():
            if any(
                hint in dependency
                for dependency in dependency_names
            ):
                databases.add(database)

    def _build_test_profile(
        self,
        root: Path,
        files: list[Path],
    ) -> BuildTestProfile:
        package_manifests = []

        for path in files:
            if path.name in {
                "package.json",
                "requirements.txt",
                "pyproject.toml",
                "Pipfile",
            }:
                package_manifests.append(
                    self._relative_path(root, path)
                )

        build_commands = []
        test_commands = []

        for path in files:
            if path.name != "package.json":
                continue

            try:
                data = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                continue

            scripts = data.get("scripts", {})

            if "build" in scripts:
                build_commands.append(
                    f"npm run build ({self._relative_path(root, path)})"
                )

            if "test" in scripts:
                test_commands.append(
                    f"npm test ({self._relative_path(root, path)})"
                )

        return BuildTestProfile(
            build_commands=sorted(set(build_commands)),
            test_commands=sorted(set(test_commands)),
            package_manifests=sorted(set(package_manifests)),
        )

    def _detect_basic_risks(
        self,
        root: Path,
        files: list[Path],
        build_test: BuildTestProfile,
    ) -> list[str]:
        risks = []

        if not build_test.build_commands:
            risks.append(
                "No build command discovered automatically."
            )

        if not build_test.test_commands:
            risks.append(
                "No test command discovered automatically."
            )

        if not any(
            self._is_documentation_file(path)
            for path in files
        ):
            risks.append(
                "No README/documentation file discovered."
            )

        return risks