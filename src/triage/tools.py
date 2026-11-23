"""
Sandboxed, read-only code exploration tools for the code-search agent.

All tools are scoped to a single target code directory.
Every access validates that paths cannot escape the target folder via
traversal (../), absolute paths, or symlinks. Sensitive directories
(.git, .venv, node_modules, .env*) and binary files are rejected or skipped.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Sequence

from langchain_core.tools import BaseTool, tool

from triage.config import settings

logger = logging.getLogger(__name__)

BINARY_EXTENSIONS = frozenset({
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib", ".bin",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".svgz",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".mov", ".avi", ".wav",
})


class SecurityError(Exception):
    """Raised when an operation attempts to escape the sandboxed directory."""


def is_ignored_name(name: str) -> bool:
    """Checks if a file or directory name should be skipped for security/noise."""
    if name in settings.ignored_names:
        return True
    if name.startswith(".env"):
        return True
    return False


def is_binary_file(file_path: Path) -> bool:
    """Checks whether a file appears to be binary by extension or null-byte check."""
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
            # Attempt decoding to catch invalid text encodings
            chunk.decode("utf-8")
            return False
    except (UnicodeDecodeError, OSError):
        return True


def resolve_safe_path(root_dir: Path, requested_path: str | Path) -> Path:
    """Resolves requested_path relative to root_dir and verifies sandbox containment.

    Raises SecurityError if the resolved path escapes root_dir or touches
    a restricted path component (.git, .venv, .env*, node_modules).
    """
    resolved_root = root_dir.resolve()
    target = Path(requested_path)

    if not target.is_absolute():
        target = resolved_root / target

    try:
        resolved_target = target.resolve()
    except Exception as exc:
        raise SecurityError(f"Cannot resolve path '{requested_path}': {exc}") from exc

    try:
        rel_target = resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise SecurityError(
            f"Access denied: path '{requested_path}' escapes code directory '{resolved_root}'."
        ) from exc

    for part in rel_target.parts:
        if is_ignored_name(part):
            raise SecurityError(
                f"Access denied: path contains restricted component '{part}'."
            )

    return resolved_target


def create_code_tools(code_dir: str | Path) -> list[BaseTool]:
    """Factory creating the sandboxed tools bound to a specific code directory."""
    root_dir = Path(code_dir).resolve()

    if not root_dir.exists():
        raise ValueError(f"Code directory does not exist: {root_dir}")
    if not root_dir.is_dir():
        raise ValueError(f"Code path is not a directory: {root_dir}")

    @tool
    def list_directory(path: str = ".") -> str:
        """List files and directories inside a folder within the codebase.

        Args:
            path: Relative path to the folder. Defaults to '.' (root).
        """
        logger.info("tool: list_directory(path='%s')", path)
        try:
            target = resolve_safe_path(root_dir, path)
        except SecurityError as err:
            logger.warning("tool security alert: %s", err)
            return f"Error: {err}"

        if not target.exists():
            return f"Error: Directory '{path}' does not exist."
        if not target.is_dir():
            return f"Error: '{path}' is a file, not a directory. Use read_file instead."

        try:
            entries = []
            for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if is_ignored_name(item.name):
                    continue
                kind = "[DIR] " if item.is_dir() else "[FILE]"
                entries.append(f"{kind} {item.name}")

            if not entries:
                res = f"Directory '{path}' is empty."
            else:
                res = "\n".join(entries)

            short = res[:120].replace("\n", " ")
            logger.info("tool: list_directory result: %s...", short)
            return res
        except Exception as exc:
            return f"Error reading directory '{path}': {exc}"

    @tool
    def read_file(path: str) -> str:
        """Read the text content of a file within the codebase.

        Args:
            path: Relative path to the file.
        """
        logger.info("tool: read_file(path='%s')", path)
        try:
            target = resolve_safe_path(root_dir, path)
        except SecurityError as err:
            logger.warning("tool security alert: %s", err)
            return f"Error: {err}"

        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: '{path}' is a directory, not a file. Use list_directory instead."
        if is_binary_file(target):
            return f"Error: '{path}' is a binary file and cannot be read as text."

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            total_len = len(content)

            if total_len > settings.max_file_read_chars:
                content = (
                    content[: settings.max_file_read_chars]
                    + f"\n\n... [Content truncated: showing first {settings.max_file_read_chars} of {total_len} characters]"
                )

            short = content[:100].replace("\n", " ")
            logger.info("tool: read_file read %d chars: %s...", len(content), short)
            return content
        except Exception as exc:
            return f"Error reading file '{path}': {exc}"

    @tool
    def search_code(query: str) -> str:
        """Search for a text keyword or snippet across all code files in the codebase.

        Args:
            query: The text or identifier to search for.
        """
        logger.info("tool: search_code(query='%s')", query)
        clean_query = query.strip()
        if not clean_query:
            return "Error: Search query cannot be empty."

        query_lower = clean_query.lower()
        matched_files: list[str] = []

        for current_root, dirs, files in os.walk(root_dir):
            # Prune ignored directories in-place so os.walk skips them
            dirs[:] = [d for d in dirs if not is_ignored_name(d)]

            for filename in sorted(files):
                if is_ignored_name(filename):
                    continue

                file_path = Path(current_root) / filename
                if is_binary_file(file_path):
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                if query_lower in text.lower():
                    rel_path = file_path.relative_to(root_dir).as_posix()
                    # Collect matching line numbers and short snippets
                    matching_lines = []
                    for line_num, line in enumerate(text.splitlines(), start=1):
                        if query_lower in line.lower():
                            snippet = line.strip()[:100]
                            matching_lines.append(f"  line {line_num}: {snippet}")
                            if len(matching_lines) >= 3:
                                break

                    match_info = f"- {rel_path}\n" + "\n".join(matching_lines)
                    matched_files.append(match_info)

                    if len(matched_files) >= settings.max_search_results:
                        break

            if len(matched_files) >= settings.max_search_results:
                break

        if not matched_files:
            res = f"No matches found for '{clean_query}'."
        else:
            res = f"Found {len(matched_files)} matching file(s):\n" + "\n".join(matched_files)

        short = res[:120].replace("\n", " ")
        logger.info("tool: search_code result: %s...", short)
        return res

    return [list_directory, read_file, search_code]
