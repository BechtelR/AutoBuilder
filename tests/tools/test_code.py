"""Tests for code analysis tools (tree-sitter symbols, diagnostics)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.tools.code import code_symbols, run_diagnostics

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# code_symbols
# ---------------------------------------------------------------------------


class TestCodeSymbols:
    def test_extracts_class_and_function(self, tmp_path: Path) -> None:
        src = tmp_path / "sample.py"
        src.write_text("class MyClass:\n    pass\n\ndef my_function():\n    return 1\n")

        result = code_symbols(str(src))
        assert "class MyClass" in result
        assert "function my_function" in result
        # Line numbers present
        assert "(line " in result

    def test_autodetects_language_from_extension(self, tmp_path: Path) -> None:
        src = tmp_path / "example.py"
        src.write_text("def hello():\n    pass\n")

        result = code_symbols(str(src))
        assert "function hello" in result

    def test_unsupported_extension_returns_message(self, tmp_path: Path) -> None:
        src = tmp_path / "data.csv"
        src.write_text("a,b,c\n1,2,3\n")

        result = code_symbols(str(src))
        assert "not supported" in result.lower() or "Supported" in result

    def test_explicit_language_override(self, tmp_path: Path) -> None:
        src = tmp_path / "noext"
        src.write_text("class Foo:\n    pass\n")

        result = code_symbols(str(src), language="python")
        assert "class Foo" in result

    def test_file_not_found(self) -> None:
        result = code_symbols("/tmp/nonexistent_file_abc123.py")
        assert "File not found" in result

    def test_no_symbols_returns_message(self, tmp_path: Path) -> None:
        src = tmp_path / "empty.py"
        src.write_text("# Just a comment\nx = 1\n")

        result = code_symbols(str(src))
        assert "No top-level symbols found" in result or "const" in result.lower()

    def test_extracts_javascript_symbols(self, tmp_path: Path) -> None:
        src = tmp_path / "app.js"
        src.write_text("function greet(name) { return name; }\nclass Widget { constructor() {} }\n")

        result = code_symbols(str(src))
        assert "function greet" in result
        assert "class Widget" in result


# ---------------------------------------------------------------------------
# run_diagnostics
# ---------------------------------------------------------------------------


class TestRunDiagnostics:
    async def test_clean_python_file_passes(self, tmp_path: Path) -> None:
        src = tmp_path / "clean.py"
        src.write_text("x: int = 1\n")

        result = await run_diagnostics(str(src))
        assert "passed" in result.lower() or "No diagnostics" in result

    async def test_python_file_with_lint_issues(self, tmp_path: Path) -> None:
        src = tmp_path / "messy.py"
        # Unused import triggers ruff F401
        src.write_text("import os\nimport sys\n\nx = 1\n")

        result = await run_diagnostics(str(src))
        # ruff should report unused imports
        assert "F401" in result or "imported but unused" in result.lower() or "os" in result

    async def test_file_not_found(self) -> None:
        result = await run_diagnostics("/tmp/nonexistent_abc123.py")
        assert "File not found" in result

    async def test_unsupported_extension(self, tmp_path: Path) -> None:
        src = tmp_path / "data.csv"
        src.write_text("a,b,c\n")

        result = await run_diagnostics(str(src))
        assert "Cannot detect tool" in result or "Supported" in result
