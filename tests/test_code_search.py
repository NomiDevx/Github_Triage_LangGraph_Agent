"""
Unit tests for the code_search agent node.

Tests verify:
- Graceful handling when no code_dir is provided.
- Graceful handling when code_dir does not exist.
- Successful extraction and path normalization from agent output.
- Graceful handling when agent hits recursion limit or raises an exception.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from triage.models import CodeSearchResult, TriageState
from triage.nodes.code_search import code_search_node


def make_state(
    title: str = "Crash in processor",
    body: str = "AttributeError: NoneType has no attribute strip",
    code_dir: str | None = None,
) -> TriageState:
    state: TriageState = {
        "issue_title": title,
        "issue_body": body,
        "category": "bug",
    }
    if code_dir is not None:
        state["code_dir"] = code_dir
    return state


def test_code_search_no_code_dir():
    state = make_state(code_dir=None)
    result = code_search_node(state)

    assert result["likely_files"] == []
    assert "No code directory provided" in result["summary"]


def test_code_search_invalid_code_dir(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    state = make_state(code_dir=str(non_existent))
    result = code_search_node(state)

    assert result["likely_files"] == []
    assert "does not exist" in result["summary"]


@patch("triage.nodes.code_search.create_agent")
def test_code_search_success_with_structured_output(mock_create_agent: MagicMock, tmp_path: Path):
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent

    mock_agent.invoke.return_value = {
        "structured_response": CodeSearchResult(
            likely_files=["src/processor.py", "src\\cli.py"],
            summary="Found processor.py where strip() is called without null check.",
        )
    }

    state = make_state(code_dir=str(tmp_path))
    result = code_search_node(state)

    # Windows backslashes should be normalized to forward slashes
    assert result["likely_files"] == ["src/processor.py", "src/cli.py"]
    assert "processor.py" in result["summary"]


@patch("triage.nodes.code_search.create_agent")
def test_code_search_agent_handles_recursion_error(mock_create_agent: MagicMock, tmp_path: Path):
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent
    mock_agent.invoke.side_effect = RuntimeError("Recursion limit of 10 reached")

    state = make_state(code_dir=str(tmp_path))
    result = code_search_node(state)

    assert result["likely_files"] == []
    assert "Code search stopped before completion" in result["summary"]
