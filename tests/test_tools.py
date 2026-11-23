"""
Unit and security tests for sandboxed code-search tools.

Proves that:
1. Relative path escapes (../) and absolute path escapes are blocked.
2. Symlink escapes pointing outside the root folder are blocked.
3. Sensitive paths (.env, .git, .venv, node_modules) are refused and excluded from listing/search.
4. Binary files are detected and rejected.
5. Large files are truncated according to config.
6. Normal operations (search, read, list) succeed cleanly.
"""

from pathlib import Path
import os
import pytest

from triage.config import settings
from triage.tools import (
    SecurityError,
    create_code_tools,
    is_binary_file,
    is_ignored_name,
    resolve_safe_path,
)


@pytest.fixture
def sandbox_env(tmp_path: Path):
    """Sets up a sandboxed repository tree for testing tools and security."""
    code_dir = tmp_path / "repo"
    code_dir.mkdir()

    # Regular source files
    src_dir = code_dir / "src"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def main():\n    print('Hello World')\n", encoding="utf-8")
    (src_dir / "processor.py").write_text(
        "def process_items(items):\n    # Process data\n    return [item.strip() for item in items]\n",
        encoding="utf-8",
    )
    (code_dir / "README.md").write_text("# Test Repo\nDocumentation here.", encoding="utf-8")

    # Sensitive files and dirs to ignore
    (code_dir / ".env").write_text("SECRET_KEY=supersecret\n", encoding="utf-8")
    (code_dir / ".env.local").write_text("LOCAL_SECRET=foo\n", encoding="utf-8")

    git_dir = code_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("git config dummy", encoding="utf-8")

    venv_dir = code_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = /bin", encoding="utf-8")

    node_dir = code_dir / "node_modules"
    node_dir.mkdir()
    (node_dir / "package.json").write_text("{}", encoding="utf-8")

    # Binary file
    (src_dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    # File outside the sandbox
    outside_file = tmp_path / "outside_secret.txt"
    outside_file.write_text("SUPER_SECRET_EXTERNAL_DATA", encoding="utf-8")

    return {
        "root": code_dir,
        "outside": outside_file,
        "tmp_root": tmp_path,
    }


def get_tool_map(code_dir: Path):
    tools = create_code_tools(code_dir)
    return {t.name: t for t in tools}


# ---------------------------------------------------------------------------
# Security & Path Escape Tests
# ---------------------------------------------------------------------------


def test_resolve_safe_path_blocks_parent_traversal(sandbox_env):
    root = sandbox_env["root"]
    with pytest.raises(SecurityError, match="escapes code directory"):
        resolve_safe_path(root, "../outside_secret.txt")

    with pytest.raises(SecurityError, match="escapes code directory"):
        resolve_safe_path(root, "../../foo/bar")


def test_resolve_safe_path_blocks_absolute_escape(sandbox_env):
    root = sandbox_env["root"]
    outside = sandbox_env["outside"]
    with pytest.raises(SecurityError, match="escapes code directory"):
        resolve_safe_path(root, str(outside.resolve()))


def test_resolve_safe_path_blocks_symlink_escape(sandbox_env):
    root = sandbox_env["root"]
    outside = sandbox_env["outside"]
    symlink_path = root / "symlink_escape.txt"

    try:
        os.symlink(outside, symlink_path)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation requires elevated permissions on this OS")

    with pytest.raises(SecurityError, match="escapes code directory"):
        resolve_safe_path(root, "symlink_escape.txt")


def test_read_file_tool_refuses_traversal(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    read_file = tools["read_file"]

    res = read_file.invoke({"path": "../outside_secret.txt"})
    assert "Error:" in res
    assert "escapes" in res.lower() or "denied" in res.lower()


def test_read_file_tool_refuses_sensitive_files(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    read_file = tools["read_file"]

    for sensitive in [".env", ".env.local", ".git/config", ".venv/pyvenv.cfg"]:
        res = read_file.invoke({"path": sensitive})
        assert "Error:" in res
        assert "restricted" in res.lower() or "denied" in res.lower()


def test_list_directory_excludes_ignored_directories(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    list_dir = tools["list_directory"]

    res = list_dir.invoke({"path": "."})
    assert "src" in res
    assert "README.md" in res
    # Restricted directories and .env files must never appear
    assert ".env" not in res
    assert ".git" not in res
    assert ".venv" not in res
    assert "node_modules" not in res


def test_list_directory_blocks_path_escape(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    list_dir = tools["list_directory"]

    res = list_dir.invoke({"path": "../../"})
    assert "Error:" in res


# ---------------------------------------------------------------------------
# Binary Files & Truncation
# ---------------------------------------------------------------------------


def test_binary_file_detection(sandbox_env):
    root = sandbox_env["root"]
    png_file = root / "src" / "logo.png"
    assert is_binary_file(png_file) is True

    text_file = root / "src" / "app.py"
    assert is_binary_file(text_file) is False


def test_read_file_refuses_binary_file(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    read_file = tools["read_file"]

    res = read_file.invoke({"path": "src/logo.png"})
    assert "Error:" in res
    assert "binary file" in res


def test_read_file_truncates_large_files(sandbox_env, monkeypatch):
    root = sandbox_env["root"]
    large_file = root / "src" / "large.txt"
    large_file.write_text("A" * 10_000, encoding="utf-8")

    from triage.config import Settings
    monkeypatch.setattr("triage.tools.settings", Settings(max_file_read_chars=500))

    tools = get_tool_map(root)
    read_file = tools["read_file"]

    res = read_file.invoke({"path": "src/large.txt"})
    assert "[Content truncated:" in res
    assert len(res) < 1000


# ---------------------------------------------------------------------------
# Functional Tool Capabilities
# ---------------------------------------------------------------------------


def test_read_file_success(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    read_file = tools["read_file"]

    res = read_file.invoke({"path": "src/app.py"})
    assert "def main():" in res
    assert "print('Hello World')" in res


def test_read_file_non_existent(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    read_file = tools["read_file"]

    res = read_file.invoke({"path": "src/missing.py"})
    assert "Error: File 'src/missing.py' does not exist." in res


def test_search_code_finds_keyword(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    search = tools["search_code"]

    res = search.invoke({"query": "process_items"})
    assert "src/processor.py" in res
    assert "line 1:" in res


def test_search_code_skips_ignored_and_binary_files(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    search = tools["search_code"]

    # Search for string present only in .env
    res = search.invoke({"query": "supersecret"})
    assert "No matches found" in res

    # Search for string in .git
    res = search.invoke({"query": "dummy"})
    assert "No matches found" in res


def test_search_code_empty_query(sandbox_env):
    tools = get_tool_map(sandbox_env["root"])
    search = tools["search_code"]

    res = search.invoke({"query": "   "})
    assert "Error: Search query cannot be empty." in res
