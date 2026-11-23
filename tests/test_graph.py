"""
Integration tests for the full triage LangGraph routing and compilation.

Tests verify:
- Graph compiles with all nodes and edges.
- Bug issues execute classify -> missing_info -> code_search.
- Non-bug issues execute classify and terminate directly at END.
"""

from unittest.mock import MagicMock, patch

import pytest

from triage.graph import build_graph
from triage.models import ClassifyResult, IssueCategory, MissingInfoResult


@patch("triage.nodes.code_search.create_agent")
@patch("triage.nodes.missing_info.llm")
@patch("triage.nodes.classify.llm")
def test_graph_routes_bug_through_all_nodes(
    mock_classify_llm: MagicMock,
    mock_missing_llm: MagicMock,
    mock_create_agent: MagicMock,
    tmp_path,
):
    # Setup mocks
    mock_classify_llm.with_structured_output.return_value.invoke.return_value = ClassifyResult(
        category=IssueCategory.BUG, confidence=0.95, reasoning="Traceback included."
    )
    mock_missing_llm.with_structured_output.return_value.invoke.return_value = MissingInfoResult(
        is_complete=True, missing_fields=[], draft_reply=""
    )
    mock_agent = MagicMock()
    mock_create_agent.return_value = mock_agent
    mock_agent.invoke.return_value = {
        "structured_response": {
            "likely_files": ["src/app.py"],
            "summary": "Identified crash location.",
        }
    }

    graph = build_graph()
    initial_state = {
        "issue_title": "App crashes",
        "issue_body": "Crash log here",
        "code_dir": str(tmp_path),
    }

    result = graph.invoke(initial_state)

    assert result["category"] == "bug"
    assert result["is_complete"] is True
    assert result["likely_files"] == ["src/app.py"]


@patch("triage.nodes.code_search.create_agent")
@patch("triage.nodes.missing_info.llm")
@patch("triage.nodes.classify.llm")
def test_graph_routes_non_bug_directly_to_end(
    mock_classify_llm: MagicMock,
    mock_missing_llm: MagicMock,
    mock_create_agent: MagicMock,
):
    mock_classify_llm.with_structured_output.return_value.invoke.return_value = ClassifyResult(
        category=IssueCategory.FEATURE_REQUEST, confidence=0.90, reasoning="User wants new feature."
    )

    graph = build_graph()
    initial_state = {
        "issue_title": "Add dark mode",
        "issue_body": "Please add dark mode support",
    }

    result = graph.invoke(initial_state)

    assert result["category"] == "feature_request"
    # missing_info and code_search must NOT have run
    assert "is_complete" not in result
    assert "likely_files" not in result
    mock_missing_llm.with_structured_output.return_value.invoke.assert_not_called()
    mock_create_agent.assert_not_called()
