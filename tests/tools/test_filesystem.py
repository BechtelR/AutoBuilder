"""Comprehensive tests for filesystem tools.

All tools are synchronous, return ``str``, use real filesystem via ``project_dir`` fixture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.tools.filesystem import (
    directory_list,
    file_delete,
    file_edit,
    file_glob,
    file_grep,
    file_insert,
    file_move,
    file_multi_edit,
    file_read,
    file_write,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# ---------------------------------------------------------------------------
# 1. file_read
# ---------------------------------------------------------------------------


class TestFileRead:
    def test_reads_existing_file(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_read(root, "hello.txt")
        assert "Hello, world!" in result
        # Should have line number prefix
        assert "1\t" in result

    def test_offset_and_limit(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "multi.txt").write_text("line1\nline2\nline3\nline4\nline5\n")
        result = file_read(root, "multi.txt", offset=2, limit=2)
        assert "line2" in result
        assert "line3" in result
        assert "line1" not in result
        assert "line4" not in result

    def test_nonexistent_file_returns_error(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_read(root, "nope.txt")
        assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# 2. file_write
# ---------------------------------------------------------------------------


class TestFileWrite:
    def test_creates_file_returns_byte_count(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_write(root, "new.txt", "hello")
        assert "5 bytes" in result
        assert (project_dir / "new.txt").read_text() == "hello"

    def test_creates_parent_dirs(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_write(root, "a/b/c.txt", "deep")
        assert "4 bytes" in result
        assert (project_dir / "a" / "b" / "c.txt").read_text() == "deep"

    def test_overwrites_existing(self, project_dir: Path) -> None:
        root = str(project_dir)
        file_write(root, "hello.txt", "replaced")
        assert (project_dir / "hello.txt").read_text() == "replaced"


# ---------------------------------------------------------------------------
# 3. file_edit
# ---------------------------------------------------------------------------


class TestFileEdit:
    def test_replaces_old_with_new(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_edit(root, "hello.txt", "Hello, world!", "Goodbye, world!")
        assert "Replaced 1" in result
        assert (project_dir / "hello.txt").read_text() == "Goodbye, world!\n"

    def test_already_edited_idempotent(self, project_dir: Path) -> None:
        root = str(project_dir)
        # First edit
        file_edit(root, "hello.txt", "Hello, world!", "Goodbye, world!")
        # Second call with same args -- old is gone but new is present
        result = file_edit(root, "hello.txt", "Hello, world!", "Goodbye, world!")
        assert result == "Already edited"

    def test_replace_all_replaces_every_occurrence(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "multi_occur.txt").write_text("aaa bbb aaa ccc aaa\n")
        result = file_edit(root, "multi_occur.txt", "aaa", "ZZZ", replace_all=True)
        assert "Replaced 3" in result
        assert (project_dir / "multi_occur.txt").read_text() == "ZZZ bbb ZZZ ccc ZZZ\n"

    def test_multi_occur_without_replace_all_errors(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "dup.txt").write_text("aaa bbb aaa\n")
        result = file_edit(root, "dup.txt", "aaa", "ZZZ")
        assert result.startswith("Error:")
        assert "found 2 times" in result
        # File should be unchanged
        assert (project_dir / "dup.txt").read_text() == "aaa bbb aaa\n"

    def test_error_when_neither_found(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_edit(root, "hello.txt", "NONEXISTENT", "replacement")
        assert result.startswith("Error:")
        assert "not found" in result


# ---------------------------------------------------------------------------
# 4. file_insert
# ---------------------------------------------------------------------------


class TestFileInsert:
    def test_inserts_at_correct_line(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "lines.txt").write_text("aaa\nbbb\nccc\n")
        result = file_insert(root, "lines.txt", 2, "INSERTED")
        assert "Inserted 1 line(s) at line 2" in result
        lines = (project_dir / "lines.txt").read_text().splitlines()
        assert lines == ["aaa", "INSERTED", "bbb", "ccc"]


# ---------------------------------------------------------------------------
# 5. file_multi_edit
# ---------------------------------------------------------------------------


class TestFileMultiEdit:
    def test_applies_multiple_edits(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "multi.txt").write_text("foo bar baz\n")
        result = file_multi_edit(
            root,
            "multi.txt",
            [{"old": "foo", "new": "FOO"}, {"old": "baz", "new": "BAZ"}],
        )
        assert "Applied 2 edit(s)" in result
        assert (project_dir / "multi.txt").read_text() == "FOO bar BAZ\n"

    def test_fails_on_missing_keys(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "keys.txt").write_text("content\n")
        result = file_multi_edit(
            root,
            "keys.txt",
            [{"old": "content"}],  # type: ignore[typeddict-item]
        )
        assert result.startswith("Error:")
        assert "missing" in result.lower()

    def test_fails_atomically_if_old_not_found(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "atomic.txt").write_text("alpha beta\n")
        result = file_multi_edit(
            root,
            "atomic.txt",
            [{"old": "alpha", "new": "ALPHA"}, {"old": "MISSING", "new": "X"}],
        )
        assert result.startswith("Error:")
        # File should be unchanged
        assert (project_dir / "atomic.txt").read_text() == "alpha beta\n"


# ---------------------------------------------------------------------------
# 6. file_glob
# ---------------------------------------------------------------------------


class TestFileGlob:
    def test_finds_matching_files(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_glob(root, "**/*.py")
        assert "sub/nested.py" in result

    def test_returns_relative_paths(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_glob(root, "**/*.txt")
        assert "hello.txt" in result
        # Should not contain the absolute tmp_path prefix
        assert root not in result

    def test_sort_by_mtime_newest_first(self, project_dir: Path) -> None:
        import time

        root = str(project_dir)
        # Create files with distinct mtimes
        (project_dir / "old.py").write_text("old\n")
        time.sleep(0.05)
        (project_dir / "new.py").write_text("new\n")

        result = file_glob(root, "**/*.py")
        lines = result.strip().splitlines()
        # Newest (new.py) should appear before oldest (old.py)
        new_idx = next(i for i, line in enumerate(lines) if "new.py" in line)
        old_idx = next(i for i, line in enumerate(lines) if "old.py" in line)
        assert new_idx < old_idx, f"new.py ({new_idx}) should appear before old.py ({old_idx})"

    def test_no_matches_returns_message(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_glob(root, "**/*.xyz")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# 7. file_grep
# ---------------------------------------------------------------------------


class TestFileGrep:
    def test_matches_regex_in_content(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_grep(root, r"x\s*=\s*1")
        assert "nested.py" in result

    def test_returns_line_numbers(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_grep(root, "Hello")
        # Format: filename:line_number:content
        assert "hello.txt:1:" in result

    def test_context_lines_included(self, project_dir: Path) -> None:
        root = str(project_dir)
        (project_dir / "ctx.txt").write_text("aaa\nbbb\nccc\nddd\neee\n")
        result = file_grep(root, "ccc", context=1)
        # Should include one line before and one line after the match
        assert "bbb" in result
        assert "ddd" in result
        # Context lines use '-' separator, match lines use ':'
        assert "ctx.txt:3:ccc" in result
        assert "ctx.txt-2-bbb" in result
        assert "ctx.txt-4-ddd" in result
        # Group separator between match blocks
        assert "--" in result

    def test_no_matches_returns_message(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_grep(root, "ZZZZNOTFOUND")
        assert "No matches found" in result


# ---------------------------------------------------------------------------
# 8. file_move
# ---------------------------------------------------------------------------


class TestFileMove:
    def test_moves_file(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_move(root, "hello.txt", "moved.txt")
        assert "Moved" in result
        assert not (project_dir / "hello.txt").exists()
        assert (project_dir / "moved.txt").read_text() == "Hello, world!\n"


# ---------------------------------------------------------------------------
# 9. file_delete
# ---------------------------------------------------------------------------


class TestFileDelete:
    def test_removes_file(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_delete(root, "hello.txt")
        assert "Deleted" in result
        assert not (project_dir / "hello.txt").exists()

    def test_error_on_nonexistent(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = file_delete(root, "nope.txt")
        assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# 10. directory_list
# ---------------------------------------------------------------------------


class TestDirectoryList:
    def test_returns_tree(self, project_dir: Path) -> None:
        root = str(project_dir)
        result = directory_list(root, ".")
        assert "hello.txt" in result
        assert "sub/" in result

    def test_depth_control(self, project_dir: Path) -> None:
        root = str(project_dir)
        # Create deeper nesting
        (project_dir / "a" / "b" / "c").mkdir(parents=True)
        (project_dir / "a" / "b" / "c" / "deep.txt").write_text("deep\n")

        # depth=1 should show "a/" but not contents inside "a/b/c/"
        result = directory_list(root, ".", depth=1)
        assert "a/" in result
        assert "deep.txt" not in result


# ---------------------------------------------------------------------------
# 11. Path traversal
# ---------------------------------------------------------------------------


_TRAVERSAL_CASES: list[Callable[[str], str]] = [
    lambda root: file_read(root, "../etc/passwd"),
    lambda root: file_write(root, "../escape.txt", "bad"),
    lambda root: file_edit(root, "../escape.txt", "a", "b"),
    lambda root: file_delete(root, "../escape.txt"),
    lambda root: file_move(root, "../escape.txt", "ok.txt"),
    lambda root: file_move(root, "hello.txt", "../escape.txt"),
    lambda root: file_insert(root, "../escape.txt", 1, "bad"),
    lambda root: file_glob(root, "*.txt", path="../"),
    lambda root: file_grep(root, "secret", path="../"),
    lambda root: directory_list(root, "../"),
]


class TestPathTraversal:
    @pytest.mark.parametrize(
        "tool_call",
        _TRAVERSAL_CASES,
        ids=[
            "read",
            "write",
            "edit",
            "delete",
            "move_src",
            "move_dst",
            "insert",
            "glob",
            "grep",
            "directory_list",
        ],
    )
    def test_traversal_rejected(self, project_dir: Path, tool_call: Callable[[str], str]) -> None:
        root = str(project_dir)
        result = tool_call(root)
        assert "Error:" in result
        assert "traversal" in result.lower() or "outside" in result.lower()
