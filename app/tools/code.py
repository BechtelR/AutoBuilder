"""Code analysis tools for ADK agents.

Provides source-code symbol extraction (tree-sitter) and linter/type-checker
diagnostics.  All functions return ``str`` and never raise exceptions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from app.lib.logging import get_logger
from app.tools._shared import truncate_output

logger = get_logger("tools.code")

# ---------------------------------------------------------------------------
# Tree-sitter language registry
# ---------------------------------------------------------------------------

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())

_EXT_TO_LANGUAGE: dict[str, Language] = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
}

_LANG_NAME_TO_LANGUAGE: dict[str, Language] = {
    "python": PY_LANGUAGE,
    "javascript": JS_LANGUAGE,
    "typescript": TS_LANGUAGE,
    "tsx": TSX_LANGUAGE,
    "jsx": JS_LANGUAGE,
}

SUPPORTED_EXTENSIONS = ", ".join(sorted(_EXT_TO_LANGUAGE.keys()))

# ---------------------------------------------------------------------------
# Python symbol extraction
# ---------------------------------------------------------------------------


def _extract_python_symbols(root: Node) -> list[str]:
    """Extract symbols from a Python parse tree."""
    symbols: list[str] = []

    for node in root.children:
        line = node.start_point[0] + 1

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"class {name} (line {line})")

        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"function {name} (line {line})")

        elif node.type in ("import_statement", "import_from_statement"):
            text = node.text.decode() if node.text else ""
            symbols.append(f"import {text} (line {line})")

        elif node.type == "decorated_definition":
            for child in node.children:
                if child.type == "class_definition":
                    name_node = child.child_by_field_name("name")
                    name = name_node.text.decode() if name_node and name_node.text else "?"
                    symbols.append(f"class {name} (line {line})")
                elif child.type == "function_definition":
                    name_node = child.child_by_field_name("name")
                    name = name_node.text.decode() if name_node and name_node.text else "?"
                    symbols.append(f"function {name} (line {line})")

    return symbols


# ---------------------------------------------------------------------------
# JS/TS symbol extraction
# ---------------------------------------------------------------------------


def _extract_js_symbols(root: Node) -> list[str]:
    """Extract symbols from a JavaScript/TypeScript parse tree."""
    symbols: list[str] = []

    for node in root.children:
        line = node.start_point[0] + 1

        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"class {name} (line {line})")

        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"function {name} (line {line})")

        elif node.type == "import_statement":
            text = node.text.decode() if node.text else ""
            symbols.append(f"import {text} (line {line})")

        elif node.type == "export_statement":
            _extract_export(node, symbols, line)

        elif node.type == "lexical_declaration":
            _extract_lexical(node, symbols, line)

    return symbols


def _extract_export(node: Node, symbols: list[str], line: int) -> None:
    """Extract symbols from an export_statement node."""
    for child in node.children:
        if child.type == "function_declaration":
            name_node = child.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"export function {name} (line {line})")
        elif child.type == "class_declaration":
            name_node = child.child_by_field_name("name")
            name = name_node.text.decode() if name_node and name_node.text else "?"
            symbols.append(f"export class {name} (line {line})")
        elif child.type == "lexical_declaration":
            _extract_lexical(child, symbols, line, exported=True)


def _extract_lexical(
    node: Node,
    symbols: list[str],
    line: int,
    *,
    exported: bool = False,
) -> None:
    """Extract arrow function or const declarations from a lexical_declaration."""
    prefix = "export " if exported else ""
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if name_node and name_node.text and value_node:
                name = name_node.text.decode()
                if value_node.type == "arrow_function":
                    symbols.append(f"{prefix}arrow_function {name} (line {line})")
                else:
                    symbols.append(f"{prefix}const {name} (line {line})")


# ---------------------------------------------------------------------------
# 1. code_symbols
# ---------------------------------------------------------------------------


def code_symbols(path: str, language: str | None = None) -> str:
    """Extract symbols (classes, functions, imports) via tree-sitter.

    Language auto-detected from extension. Returns a newline-separated
    list of symbols with their types and line numbers. Supports Python,
    JavaScript, and TypeScript files.

    Args:
        path: Absolute path to the source file to analyse.
        language: Optional language override (python, javascript, typescript,
            tsx, jsx).  When omitted the language is detected from the file
            extension.

    Returns:
        A formatted string listing each symbol, or an error description.
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            return f"File not found: {path}"

        if not file_path.is_file():
            return f"Not a file: {path}"

        # Resolve language
        lang: Language | None = None
        if language is not None:
            lang = _LANG_NAME_TO_LANGUAGE.get(language.lower())
            if lang is None:
                supported = ", ".join(sorted(_LANG_NAME_TO_LANGUAGE.keys()))
                return f"Language not supported: {language}. Supported: {supported}"
        else:
            ext = file_path.suffix.lower()
            lang = _EXT_TO_LANGUAGE.get(ext)
            if lang is None:
                return f"Language not supported: {ext}. Supported: {SUPPORTED_EXTENSIONS}"

        source = file_path.read_bytes()
        parser = Parser(lang)
        tree = parser.parse(source)

        is_python = lang is PY_LANGUAGE
        if is_python:
            symbols = _extract_python_symbols(tree.root_node)
        else:
            symbols = _extract_js_symbols(tree.root_node)

        if not symbols:
            return "No top-level symbols found."

        return truncate_output("\n".join(symbols))

    except Exception as exc:
        logger.debug("code_symbols failed for %s: %s", path, exc)
        return f"Error analysing {path}: {exc}"


# ---------------------------------------------------------------------------
# 2. run_diagnostics
# ---------------------------------------------------------------------------

_EXT_TO_TOOL: dict[str, str] = {
    ".py": "ruff",
    ".js": "tsc",
    ".jsx": "tsc",
    ".ts": "tsc",
    ".tsx": "tsc",
}

_SUPPORTED_TOOLS = {"ruff", "tsc"}


async def run_diagnostics(path: str, tool: str | None = None) -> str:
    """Run lint or type-check on a file. Tool selection configurable per project.

    Auto-detects the appropriate tool from the file extension when *tool* is
    not provided: ``.py`` files use **ruff**, and ``.ts``/``.js``/``.tsx``/
    ``.jsx`` files use **tsc**.

    Args:
        path: Absolute path to the source file to check.
        tool: Optional tool override (``ruff`` or ``tsc``).  When omitted the
            tool is inferred from the file extension.

    Returns:
        The diagnostic output (possibly truncated), or an error description.
    """
    try:
        file_path = Path(path)

        if not file_path.exists():
            return f"File not found: {path}"

        if not file_path.is_file():
            return f"Not a file: {path}"

        # Resolve tool
        selected_tool: str | None = tool
        if selected_tool is None:
            ext = file_path.suffix.lower()
            selected_tool = _EXT_TO_TOOL.get(ext)
            if selected_tool is None:
                supported_exts = ", ".join(sorted(_EXT_TO_TOOL.keys()))
                return (
                    f"Cannot detect tool for extension: {ext}. "
                    f"Supported extensions: {supported_exts}"
                )
        else:
            selected_tool = selected_tool.lower()

        if selected_tool not in _SUPPORTED_TOOLS:
            return (
                f"Unknown tool: {selected_tool}. Supported: {', '.join(sorted(_SUPPORTED_TOOLS))}"
            )

        # Build command
        if selected_tool == "ruff":
            cmd = ["ruff", "check", str(file_path)]
        else:
            cmd = ["npx", "tsc", "--noEmit", str(file_path)]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout_bytes, _ = await proc.communicate()
        output = stdout_bytes.decode(errors="replace").strip()

        if not output:
            return f"No diagnostics found ({selected_tool} passed)."

        return truncate_output(output)

    except FileNotFoundError:
        tool_name = tool or "detected tool"
        return f"Tool not found on PATH: {tool_name}. Is it installed?"
    except Exception as exc:
        logger.debug("run_diagnostics failed for %s: %s", path, exc)
        return f"Error running diagnostics on {path}: {exc}"
