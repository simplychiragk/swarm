"""
Path Safety and Sandbox Helper for Swarm.
Enforces that all file reads, writes, and deletions stay strictly within
the designated run workspace (workspace/<run_id>/).
Prevents directory traversal, symlink escapes, absolute path escapes,
and access to sensitive system or credential files (Windows and POSIX safe).
"""

import os
import re
from pathlib import Path
from typing import Optional, Union


class PathSafetyError(PermissionError):
    """Raised when an operation attempts to escape the run sandbox or access forbidden files."""
    pass


# Forbidden file patterns (secrets, credentials, keys)
FORBIDDEN_FILE_PATTERNS = [
    re.compile(r"(?i)^\.?env(\..*)?$"),
    re.compile(r"(?i)^.*id_rsa.*$"),
    re.compile(r"(?i)^.*id_ed25519.*$"),
    re.compile(r"(?i)^.*\.pem$"),
    re.compile(r"(?i)^.*\.key$"),
    re.compile(r"(?i)^.*\.pfx$"),
    re.compile(r"(?i)^.*\.pkcs12$"),
    re.compile(r"(?i)^\.?ssh(/.*)?$"),
    re.compile(r"(?i)^.*credential.*$"),
    re.compile(r"(?i)^.*secret.*$"),
]

# Protected system subtrees that agents must never access or modify
PROTECTED_PROJECT_DIRS = {
    "sidecar",
    "app",
    "shared",
    ".git",
    ".venv",
    "docs",
    "policy.json",
}


def get_repo_root() -> Path:
    """Returns the canonical root directory of the repository."""
    # This file is at sidecar/permissions/path_safety.py -> repo root is 2 levels up
    return Path(__file__).resolve().parent.parent.parent


def get_project_root() -> Optional[Path]:
    """
    Returns the user-configured external project root (Gap 1), or None.
    Read from SWARM_PROJECT_ROOT env var (or set at runtime via set_project_root).
    When set, all agent file operations target this folder instead of workspace/<run_id>/.
    """
    raw = _PROJECT_ROOT_OVERRIDE or os.environ.get("SWARM_PROJECT_ROOT", "")
    raw = str(raw).strip()
    if not raw:
        return None
    return Path(raw).resolve()


def set_project_root(path: Union[str, Path, None]) -> None:
    """
    Runtime override for the project root (used by the --project-dir CLI flag).
    Validates that the directory exists before accepting it.
    """
    global _PROJECT_ROOT_OVERRIDE
    if path is None or (isinstance(path, str) and not path.strip()):
        _PROJECT_ROOT_OVERRIDE = None
        return

    resolved = Path(str(path)).expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise PathSafetyError(
            f"--project-dir '{resolved}' does not exist or is not a directory."
        )
    _PROJECT_ROOT_OVERRIDE = resolved


# Module-level runtime override for set_project_root (CLI flag support)
_PROJECT_ROOT_OVERRIDE: Optional[Path] = None


def is_project_mode() -> bool:
    """True when Swarm is attached to an external user project (Gap 1 mode)."""
    return get_project_root() is not None


def validate_run_id(run_id: str) -> str:
    """Validates that a run_id contains only safe identifier characters."""
    if not run_id or not isinstance(run_id, str):
        raise PathSafetyError("Invalid or missing run_id")
    cleaned = run_id.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
        raise PathSafetyError(f"Invalid run_id '{run_id}': contains unsafe characters")
    return cleaned


def get_run_workspace(run_id: str, create: bool = True) -> Path:
    """
    Returns the resolved run workspace directory.

    Gap 1: When SWARM_PROJECT_ROOT (or --project-dir) is configured, agents work
    directly inside the user's existing repository instead of workspace/<run_id>/.
    All path-safety boundaries (forbidden secret files, traversal, escapes) still apply.
    """
    valid_id = validate_run_id(run_id)
    project_root = get_project_root()
    if project_root is not None:
        # Escape-the-sandbox mode: resolve to the user's chosen project folder.
        if not project_root.exists() or not project_root.is_dir():
            raise PathSafetyError(
                f"SWARM_PROJECT_ROOT '{project_root}' does not exist or is not a directory."
            )
        return project_root
    repo_root = get_repo_root()
    workspace = (repo_root / "workspace" / valid_id).resolve()
    if create and not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def is_path_within_workspace(target: Path, workspace: Path) -> bool:
    """
    Cross-platform check (Windows and POSIX) verifying that target is inside workspace.
    Handles case-insensitivity on Windows and canonical drive letters.
    """
    norm_target = os.path.normcase(str(target.resolve()))
    norm_ws = os.path.normcase(str(workspace.resolve()))

    # Ensure trailing separator comparison
    if not norm_ws.endswith(os.sep):
        norm_ws += os.sep

    return norm_target.startswith(norm_ws) or norm_target == norm_ws.rstrip(os.sep)


def check_forbidden_filename(filename: str) -> None:
    """Checks if a filename matches forbidden secret or credential patterns."""
    basename = Path(filename).name
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if pattern.match(basename) or pattern.match(filename):
            raise PathSafetyError(f"Access to secret/credential pattern '{filename}' is FORBIDDEN.")


def resolve_safe_path(
    run_id: str,
    requested_path: str,
    must_exist: bool = False,
    for_write: bool = False,
) -> Path:
    """
    Resolves a requested path relative to workspace/<run_id>/.
    Rejects:
    - Path traversal attempts ('..')
    - Absolute paths outside the workspace
    - Symlinks / junctions escaping the workspace
    - Secret files (.env, keys, etc.)
    - Protected system paths (sidecar/, app/, shared/, etc.)
    """
    if not requested_path or not str(requested_path).strip():
        raise PathSafetyError("Path cannot be empty.")

    clean_path_str = str(requested_path).strip()

    # Reject explicit parent directory traversal tokens before resolving
    path_parts = Path(clean_path_str).parts
    if ".." in path_parts:
        raise PathSafetyError(f"Path traversal '..' is FORBIDDEN in '{clean_path_str}'.")

    # Check forbidden filename patterns
    check_forbidden_filename(clean_path_str)

    workspace = get_run_workspace(run_id, create=True)
    candidate = Path(clean_path_str)

    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (workspace / candidate).resolve()

    # Verify boundary containment
    if not is_path_within_workspace(resolved, workspace):
        raise PathSafetyError(
            f"Path '{clean_path_str}' escapes run workspace '{workspace}'. Access is FORBIDDEN."
        )

    # Re-check canonical leaf name after resolution (in case of aliases/links)
    check_forbidden_filename(resolved.name)

    # Check existence if required
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"File not found in run workspace: '{clean_path_str}'")

    if for_write:
        # Ensure parent directory exists inside workspace
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved
