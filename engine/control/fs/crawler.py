import os
import re
import logging
from engine.control.config.constants import EXCLUDED_DIRS
from engine.control.parsing.markdown_ast import parse_frontmatter

logger = logging.getLogger(__name__)


def gather_markdown_paths(
    target_dirs,
    repo_root=None,
    allowed_root_dirs=None,
    ignored_files_lower=None,
    ignored_patterns=None,
):
    """
    Scans and deduplicates Markdown file paths from target directories.
    Deduplication here applies strictly to file paths (to handle overlapping input directories),
    NOT to document IDs. Enforces Fail-Closed security by strictly checking `allowed_root_dirs`
    and bypassing deeply nested exclusions. If `repo_root` is provided, it guarantees that only
    directories explicitly within the repository boundary are scanned; any external paths will
    trigger a hard crash.

    <pre>Args:
        - target_dirs (str | list): Target paths/files to scan.
        - repo_root (str, optional): Repository root for boundary validation.
        - allowed_root_dirs (set, optional): Whitelisted top-level directories. External paths
          trigger a hard crash.

    Returns:
        list: Valid Markdown file paths.

    Raises:
        SystemExit: If path traversal (e.g., `../`) or unauthorized directories are detected.
    </pre>
    """

    if isinstance(target_dirs, str):
        target_dirs = [target_dirs]

    ignored_files_lower = ignored_files_lower or []
    ignored_patterns = ignored_patterns or []

    def _is_ignored(fpath: str) -> bool:
        fname = os.path.basename(fpath)
        if fname.lower() in ignored_files_lower:
            return True

        # Ignore-patterns are path policies, not filename escape hatches.
        # Normalize separators so the same rule behaves identically on Windows and POSIX.
        normalized_path = fpath.replace("\\", "/")
        for pattern in ignored_patterns:
            if re.search(pattern, normalized_path):
                return True
        return False

    files_to_lint = []
    repo_root_abs = os.path.abspath(repo_root) if repo_root else None

    for target in target_dirs:
        if allowed_root_dirs and repo_root:
            abs_target = os.path.abspath(target)
            try:
                rel_to_root = os.path.relpath(abs_target, repo_root_abs)
            except ValueError as exc:
                # Windows raises when target and repository are on different drives.
                raise ValueError(
                    f"Target '{target}' is on a different drive than the repository. Execution blocked to prevent validation bypass."
                ) from exc

            # A target may be an allowed artifact directory, one of its descendants,
            # or a parent used to select it (for example `docs` for `docs/designs`).
            # Traversal below still strips files outside the exact allowed roots.
            if rel_to_root == os.pardir or rel_to_root.startswith(os.pardir + os.sep):
                raise ValueError(
                    f"Target '{target}' is outside the repository boundary. Execution blocked to prevent validation bypass."
                )

            if rel_to_root != ".":
                norm_rel = os.path.normpath(rel_to_root)
                is_allowed = any(
                    norm_rel == allowed_path
                    or norm_rel.startswith(allowed_path + os.sep)
                    or allowed_path.startswith(norm_rel + os.sep)
                    for allowed_path in map(os.path.normpath, allowed_root_dirs)
                )
                if not is_allowed:
                    raise ValueError(
                        f"Target '{target}' is not in allowed artifact directories. Execution blocked to prevent validation bypass."
                    )

        if os.path.isfile(target):
            if target.lower().endswith(".md") and not _is_ignored(target):
                files_to_lint.append(target)
        else:
            for root, dirs, files in os.walk(target):
                # CASE 1: Full Repository Scan (Default target = ".")
                # Logic: Because it's at the root, it STERILIZES the directory tree by aggressively pruning
                # folders like "src" or "node_modules", only entering allowed_root_dirs like "governance".
                if (
                    allowed_root_dirs
                    and repo_root
                    and os.path.abspath(root) == repo_root_abs
                ):
                    allowed_first_levels = set(
                        os.path.normpath(d).split(os.sep)[0] for d in allowed_root_dirs
                    )
                    dirs[:] = [d for d in dirs if d in allowed_first_levels]
                    files[:] = []  # Sterilize root
                else:
                    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

                if allowed_root_dirs and repo_root:
                    rel_root = os.path.relpath(os.path.abspath(root), repo_root_abs)
                    if rel_root != ".":
                        is_allowed = False
                        norm_rel = os.path.normpath(rel_root)
                        for allowed in allowed_root_dirs:
                            allowed_path = os.path.normpath(allowed)
                            if norm_rel == allowed_path or norm_rel.startswith(
                                allowed_path + os.sep
                            ):
                                is_allowed = True
                                break
                        if not is_allowed:
                            files[:] = []

                for file in files:
                    if file.lower().endswith(".md"):
                        fpath = os.path.join(root, file)
                        if not _is_ignored(fpath):
                            files_to_lint.append(fpath)

    # Deduplicate file paths while preserving order (to keep determinism).
    # This prevents scanning the exact same file twice if `target_dirs` contains overlapping directories.
    # Note: This does NOT deduplicate document IDs. Two different files with the same ID will still pass through.
    seen = set()
    unique_files = []
    for f in files_to_lint:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)

    return unique_files


def build_metadata_registry(
    target_dirs,
    repo_root=None,
    allowed_root_dirs=None,
    ignored_files_lower=None,
    ignored_patterns=None,
):
    """
    Builds a central registry of architecture documents by parsing YAML frontmatter. Enforces the
    SSOT (Single Source of Truth) invariant by detecting duplicate IDs.
    **Note**: This phase strictly GATHERS data by calling `gather_markdown_paths`. We then call
    `parse_frontmatter` but intentionally IGNORE any parsing errors (e.g., missing `doc_meta` or
    invalid YAML). This is because this phase is NOT for structural validation, its sole purpose
    is to build a registry to detect duplicate IDs. All other metadata validation is delegated to
    the main engine.

    <pre>Args:
        - target_dirs (str | list): Target directories to scan.
        - allowed_root_dirs (set, optional): Whitelisted root directories for boundary enforcement.

    Returns:
        tuple: (unique_ids, registry, duplicates)
            - unique_ids (set): Discovered document IDs.
            - registry (dict): Maps `doc_id` to its metadata (includes `_filepath`).
            - duplicates (dict): Maps duplicated `doc_id` to conflicting file paths.

    Raises:
        ValueError: If `gather_markdown_paths` detects path traversal or unauthorized boundaries.
    </pre>
    """
    if isinstance(target_dirs, str):
        target_dirs = [target_dirs]

    ids = set()
    metadata_registry = {}
    first_seen_path = {}
    duplicates = {}

    try:
        files_to_lint = gather_markdown_paths(
            target_dirs,
            repo_root,
            allowed_root_dirs,
            ignored_files_lower=ignored_files_lower,
            ignored_patterns=ignored_patterns,
        )
    except ValueError as e:
        # Explicitly forward the exception to the caller (e.g., cli.py)
        raise ValueError(str(e))

    for path in files_to_lint:
        norm_path = path.replace("\\", "/")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            doc_meta, _ = parse_frontmatter(content)
            if doc_meta:
                doc_id = doc_meta.get("id")
                if doc_id:
                    if doc_id in ids:
                        duplicates.setdefault(doc_id, [first_seen_path[doc_id]]).append(
                            norm_path
                        )
                    else:
                        ids.add(doc_id)
                        doc_meta["_filepath"] = norm_path
                        metadata_registry[doc_id] = doc_meta
                        first_seen_path[doc_id] = norm_path
        except Exception as e:
            logger.debug("Scanner skipping '%s': %s", path, e)
            continue

    return ids, metadata_registry, duplicates
