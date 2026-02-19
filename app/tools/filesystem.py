"""Filesystem tools for ADK agents.

All functions are synchronous, return ``str``, and never raise exceptions.
Paths are always relative to the ``project_root`` parameter and validated
via :func:`app.tools._shared.validate_path`.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
from pathlib import Path

from app.lib.logging import get_logger
from app.tools._shared import MAX_OUTPUT_LENGTH, truncate_output, validate_path

logger = get_logger("tools.filesystem")


# ---------------------------------------------------------------------------
# 1. file_read
# ---------------------------------------------------------------------------


def file_read(
    project_root: str,
    path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read file contents with optional line offset and limit.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.
        offset: 1-based starting line number. Defaults to the first line.
        limit: Maximum number of lines to return. Defaults to all lines.

    Returns:
        Numbered lines in ``cat -n`` format, truncated to MAX_OUTPUT_LENGTH.
    """
    try:
        resolved = validate_path(path, project_root)
        if not resolved.is_file():
            return f"Error: not a file: {path}"
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("file_read error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    lines = text.splitlines(keepends=True)

    start = (offset - 1) if offset and offset >= 1 else 0
    end = (start + limit) if limit and limit > 0 else len(lines)
    selected = lines[start:end]

    numbered: list[str] = []
    for idx, line in enumerate(selected, start=start + 1):
        numbered.append(f"{idx:>6}\t{line.rstrip()}")

    return truncate_output("\n".join(numbered))


# ---------------------------------------------------------------------------
# 2. file_write
# ---------------------------------------------------------------------------


def file_write(project_root: str, path: str, content: str) -> str:
    """Write or create a file with the given content.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.
        content: Text content to write.

    Returns:
        Confirmation with byte count written.
    """
    try:
        resolved = validate_path(path, project_root)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        resolved.write_bytes(data)
        return f"Wrote {len(data)} bytes to {path}"
    except Exception as exc:
        logger.warning("file_write error: %s", exc, extra={"path": path})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 3. file_edit
# ---------------------------------------------------------------------------


def file_edit(
    project_root: str,
    path: str,
    old: str,
    new: str,
    replace_all: bool = False,
) -> str:
    """Targeted string replacement within a file.

    Idempotent: returns success if already edited.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.
        old: Exact text to find and replace.
        new: Replacement text.
        replace_all: If True, replace every occurrence. If False and
            multiple occurrences are found, return an error.

    Returns:
        Confirmation of edits applied, or an error description.
    """
    try:
        resolved = validate_path(path, project_root)
        if not resolved.is_file():
            return f"Error: not a file: {path}"
        text = resolved.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("file_edit read error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    count = text.count(old)

    if count == 0:
        # Idempotent: if `new` is already present, treat as already edited
        if new in text:
            return "Already edited"
        return f"Error: old string not found in {path}"

    if not replace_all and count > 1:
        return (
            f"Error: old string found {count} times in {path}. "
            "Use replace_all=True or provide a more unique string."
        )

    try:
        updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        resolved.write_text(updated, encoding="utf-8")
        replaced = count if replace_all else 1
        return f"Replaced {replaced} occurrence(s) in {path}"
    except Exception as exc:
        logger.warning("file_edit write error: %s", exc, extra={"path": path})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 4. file_insert
# ---------------------------------------------------------------------------


def file_insert(project_root: str, path: str, line: int, content: str) -> str:
    """Insert content at a specific line number, shifting existing lines down.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.
        line: 1-based line number where content will be inserted.
        content: Text to insert.

    Returns:
        Confirmation or error description.
    """
    try:
        resolved = validate_path(path, project_root)
        if not resolved.is_file():
            return f"Error: not a file: {path}"
        text = resolved.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("file_insert read error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    if line < 1:
        return "Error: line number must be >= 1"

    lines = text.splitlines(keepends=True)
    insert_idx = min(line - 1, len(lines))

    # Ensure inserted content ends with newline if the file uses them
    insert_text = content if content.endswith("\n") else content + "\n"
    insert_lines = insert_text.splitlines(keepends=True)

    lines[insert_idx:insert_idx] = insert_lines

    try:
        resolved.write_text("".join(lines), encoding="utf-8")
        return f"Inserted {len(insert_lines)} line(s) at line {line} in {path}"
    except Exception as exc:
        logger.warning("file_insert write error: %s", exc, extra={"path": path})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 5. file_multi_edit
# ---------------------------------------------------------------------------


def file_multi_edit(
    project_root: str,
    path: str,
    edits: list[dict[str, str]],
) -> str:
    """Apply multiple non-overlapping edits atomically in a single pass.

    All ``old`` strings are validated before any edit is applied.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.
        edits: List of dicts each with ``"old"`` and ``"new"`` keys.

    Returns:
        Confirmation with count of edits applied, or an error description.
    """
    try:
        resolved = validate_path(path, project_root)
        if not resolved.is_file():
            return f"Error: not a file: {path}"
        text = resolved.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("file_multi_edit read error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    # Validate structure
    for i, edit in enumerate(edits):
        if "old" not in edit or "new" not in edit:
            return f"Error: edit {i} missing 'old' or 'new' key"

    # Validate all old strings exist before mutating
    for i, edit in enumerate(edits):
        if edit["old"] not in text:
            return f"Error: edit {i} old string not found in {path}"

    # Apply edits sequentially
    for edit in edits:
        text = text.replace(edit["old"], edit["new"], 1)

    try:
        resolved.write_text(text, encoding="utf-8")
        return f"Applied {len(edits)} edit(s) to {path}"
    except Exception as exc:
        logger.warning("file_multi_edit write error: %s", exc, extra={"path": path})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 6. file_glob
# ---------------------------------------------------------------------------


def file_glob(
    project_root: str,
    pattern: str,
    path: str | None = None,
) -> str:
    """Find files by name pattern (glob syntax). Returns matching paths.

    Args:
        project_root: Absolute path to the project root directory.
        path: Optional subdirectory to search within, relative to project_root.
        pattern: Glob pattern (e.g. ``"**/*.py"``).

    Returns:
        Newline-separated relative file paths, sorted by mtime (newest first).
        Limited to 500 results.
    """
    try:
        if path is not None:
            base = validate_path(path, project_root)
        else:
            base = Path(project_root).resolve()

        if not base.is_dir():
            return f"Error: not a directory: {path or project_root}"
    except Exception as exc:
        logger.warning("file_glob path error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    root = Path(project_root).resolve()
    max_results = 500

    try:
        matches: list[Path] = []
        for p in base.glob(pattern):
            if p.is_file():
                matches.append(p)
                if len(matches) > max_results * 2:
                    break

        # Sort by mtime descending
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        matches = matches[:max_results]

        relative = [str(p.relative_to(root)) for p in matches]
        if not relative:
            return "No matches found"
        return truncate_output("\n".join(relative))
    except Exception as exc:
        logger.warning("file_glob error: %s", exc, extra={"pattern": pattern})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 7. file_grep
# ---------------------------------------------------------------------------


def file_grep(
    project_root: str,
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    context: int | None = None,
) -> str:
    """Search file contents by regex pattern with optional file filtering and context lines.

    Args:
        project_root: Absolute path to the project root directory.
        pattern: Regular expression pattern to search for.
        path: Optional subdirectory to search within, relative to project_root.
        glob: Optional glob pattern to filter which files are searched.
        context: Number of context lines before and after each match.
            Defaults to 0.

    Returns:
        Matches in ``filename:line_number:content`` format, truncated to
        MAX_OUTPUT_LENGTH.
    """
    ctx = context if context is not None else 0

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"

    try:
        if path is not None:
            base = validate_path(path, project_root)
        else:
            base = Path(project_root).resolve()

        if not base.is_dir():
            return f"Error: not a directory: {path or project_root}"
    except Exception as exc:
        logger.warning("file_grep path error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    root = Path(project_root).resolve()
    output_lines: list[str] = []
    output_len = 0

    try:
        for dirpath, _dirnames, filenames in os.walk(base):
            for filename in sorted(filenames):
                filepath = Path(dirpath) / filename

                if glob and not fnmatch.fnmatch(filename, glob):
                    # Also check full relative path against glob
                    rel = str(filepath.relative_to(root))
                    if not fnmatch.fnmatch(rel, glob):
                        continue

                try:
                    text = filepath.read_text(encoding="utf-8", errors="replace")
                except (OSError, UnicodeDecodeError):
                    continue

                lines = text.splitlines()
                rel_path = str(filepath.relative_to(root))

                for line_num, line_text in enumerate(lines, start=1):
                    if regex.search(line_text):
                        # Collect context range
                        start = max(0, line_num - 1 - ctx)
                        end = min(len(lines), line_num + ctx)

                        for ctx_idx in range(start, end):
                            ctx_num = ctx_idx + 1
                            sep = ":" if ctx_num == line_num else "-"
                            entry = f"{rel_path}{sep}{ctx_num}{sep}{lines[ctx_idx]}"
                            output_lines.append(entry)
                            output_len += len(entry) + 1

                        if ctx > 0:
                            output_lines.append("--")
                            output_len += 3

                        if output_len >= MAX_OUTPUT_LENGTH:
                            break

                if output_len >= MAX_OUTPUT_LENGTH:
                    break
            if output_len >= MAX_OUTPUT_LENGTH:
                break
    except Exception as exc:
        logger.warning("file_grep error: %s", exc, extra={"pattern": pattern})
        return f"Error: {exc}"

    if not output_lines:
        return "No matches found"
    return truncate_output("\n".join(output_lines))


# ---------------------------------------------------------------------------
# 8. file_move
# ---------------------------------------------------------------------------


def file_move(project_root: str, src: str, dst: str) -> str:
    """Move or rename a file.

    Args:
        project_root: Absolute path to the project root directory.
        src: Source file path relative to project_root.
        dst: Destination file path relative to project_root.

    Returns:
        Confirmation or error description.
    """
    try:
        src_resolved = validate_path(src, project_root)
        dst_resolved = validate_path(dst, project_root)
    except Exception as exc:
        logger.warning("file_move path error: %s", exc, extra={"src": src, "dst": dst})
        return f"Error: {exc}"

    if not src_resolved.exists():
        return f"Error: source does not exist: {src}"

    try:
        dst_resolved.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_resolved), str(dst_resolved))
        return f"Moved {src} -> {dst}"
    except Exception as exc:
        logger.warning("file_move error: %s", exc, extra={"src": src, "dst": dst})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 9. file_delete
# ---------------------------------------------------------------------------


def file_delete(project_root: str, path: str) -> str:
    """Delete a file.

    Args:
        project_root: Absolute path to the project root directory.
        path: File path relative to project_root.

    Returns:
        Confirmation or error description.
    """
    try:
        resolved = validate_path(path, project_root)
    except Exception as exc:
        logger.warning("file_delete path error: %s", exc, extra={"path": path})
        return f"Error: {exc}"

    if not resolved.exists():
        return f"Error: file does not exist: {path}"
    if not resolved.is_file():
        return f"Error: not a file: {path}"

    try:
        resolved.unlink()
        return f"Deleted {path}"
    except Exception as exc:
        logger.warning("file_delete error: %s", exc, extra={"path": path})
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# 10. directory_list
# ---------------------------------------------------------------------------


def directory_list(
    project_root: str,
    path: str,
    depth: int | None = None,
) -> str:
    """List directory contents as a tree with optional depth control.

    Args:
        project_root: Absolute path to the project root directory.
        path: Directory path relative to project_root.
        depth: Maximum recursion depth. Defaults to 2.

    Returns:
        Tree listing with directories suffixed by ``/``, sorted alphabetically.
    """
    max_depth = depth if depth is not None else 2

    try:
        resolved = validate_path(path, project_root)
    except Exception as exc:
        return f"Error: {exc}"

    if not resolved.is_dir():
        return f"Error: not a directory: {path}"

    lines: list[str] = []

    def _walk(directory: Path, prefix: str, current_depth: int) -> None:
        if current_depth > max_depth:
            return

        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError:
            lines.append(f"{prefix}[permission denied]")
            return

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
            name = entry.name + ("/" if entry.is_dir() else "")
            lines.append(f"{prefix}{connector}{name}")

            if entry.is_dir() and current_depth < max_depth:
                extension = "    " if is_last else "\u2502   "
                _walk(entry, prefix + extension, current_depth + 1)

    root_name = resolved.name or path
    lines.append(f"{root_name}/")
    _walk(resolved, "", 1)

    return truncate_output("\n".join(lines))
