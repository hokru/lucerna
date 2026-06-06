import os
import fnmatch
from pathlib import Path
from typing import List, Tuple

DEFAULT_EXCLUDES = [
    "venv",
    ".venv",
    "env",
    ".env",
    ".*",
    "__pycache__",
    "dist",
    "build",
    "*.egg-info",
    "site-packages",
    "node_modules",
]


def should_exclude(path: Path, root: Path, exclude_patterns: List[str]) -> bool:
    """Check if a path should be excluded based on fnmatch patterns."""
    rel_path = str(path.relative_to(root))
    name = path.name

    for pattern in exclude_patterns:
        # Match either the filename or the relative path
        if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
            return True

        # Match directory prefixes (e.g. if pattern is 'venv', ignore 'venv/*')
        if pattern in path.parts:
            return True

    return False


def scan_directory(
    root_dir: str, exclude_patterns: List[str] = None
) -> List[Tuple[str, str, str]]:
    """
    Scans a directory for python and C++ binding files, respecting exclusions.
    Returns:
        List of tuples: (absolute_path, root_relative_path, file_type)
        where file_type is 'python' or 'cpp'.
    """
    if exclude_patterns is None:
        exclude_patterns = list(DEFAULT_EXCLUDES)
    else:
        exclude_patterns = list(exclude_patterns)

    root = Path(root_dir).resolve()

    # Read .codetreeignore if present
    ignore_file = root / ".codetreeignore"
    if ignore_file.is_file():
        try:
            with open(ignore_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        exclude_patterns.append(stripped)
        except Exception:
            pass

    results = []

    for current_dir, dirs, files in os.walk(root):
        current_path = Path(current_dir)

        # Modify dirs in-place to prune excluded directories from os.walk
        dirs[:] = [
            d
            for d in dirs
            if not should_exclude(current_path / d, root, exclude_patterns)
        ]

        for f in files:
            file_path = current_path / f
            if file_path.suffix == ".py":
                file_type = "python"
            elif file_path.suffix in (".cpp", ".cc", ".cxx", ".c"):
                file_type = "cpp"
            else:
                continue

            if not should_exclude(file_path, root, exclude_patterns):
                results.append(
                    (str(file_path), str(file_path.relative_to(root)), file_type)
                )

    return results
