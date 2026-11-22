from pathlib import Path


class UnsafePathError(ValueError):
    pass


def safe_resolve(
    base: Path,
    relative_path: str,
    allowed_root: Path | None = None,
) -> Path:
    """
    Resolve a relative path from `base` while ensuring the
    resulting path remains inside `allowed_root`.

    If allowed_root is not provided, `base` is used as the
    security boundary.
    """
    base_resolved = base.resolve()
    root_resolved = (
        allowed_root.resolve()
        if allowed_root is not None
        else base_resolved
    )

    candidate = (base_resolved / relative_path).resolve()

    if not candidate.is_relative_to(root_resolved):
        raise UnsafePathError(
            f"Path escapes allowed directory: {relative_path}"
        )

    return candidate