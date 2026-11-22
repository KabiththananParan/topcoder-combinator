from pathlib import Path
import os


class WorkspaceSecurityError(ValueError):
    """Raised when a filesystem operation escapes its allowed boundary."""


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    """
    Resolve a relative path while enforcing the root boundary.

    Security rules:
    - Absolute paths are rejected.
    - '..' traversal outside root is rejected.
    - Existing symlink components are rejected.
    - The returned path remains inside root.
    """

    root_resolved = root.resolve()

    relative = Path(relative_path)

    # Reject absolute paths.
    if relative.is_absolute():
        raise WorkspaceSecurityError(
            f"Path escapes workspace: {relative_path}"
        )

    # Normalize the path lexically so '..' is evaluated before
    # filesystem resolution.
    normalized = Path(os.path.normpath(relative_path))

    candidate = root_resolved / normalized

    # Check the normalized lexical path against the root.
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise WorkspaceSecurityError(
            f"Path escapes workspace: {relative_path}"
        )

    # Reject symlink components before calling resolve().
    current = candidate

    while current != root_resolved:
        if current.is_symlink():
            raise WorkspaceSecurityError(
                f"symlink path is not allowed: {relative_path}"
            )

        current = current.parent

    # Resolve the final path and perform one final boundary check.
    resolved_candidate = candidate.resolve()

    try:
        resolved_candidate.relative_to(root_resolved)
    except ValueError:
        raise WorkspaceSecurityError(
            f"Path escapes workspace: {relative_path}"
        )

    return resolved_candidate