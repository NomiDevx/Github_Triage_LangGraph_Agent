"""
Unit tests for the missing_info node.

The LLM is mocked throughout. Tests verify the node's output shape,
the is_complete=True fast path, the is_complete=False path with
missing fields and a draft reply, and error propagation.
"""

from unittest.mock import MagicMock, patch

import pytest

from triage.models import MissingInfoResult, TriageState
from triage.nodes.missing_info import missing_info_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(title: str = "Some bug", body: str = "It broke.") -> TriageState:
    return {"issue_title": title, "issue_body": body}


def patch_llm(mock_llm: MagicMock, result: MissingInfoResult) -> None:
    mock_llm.with_structured_output.return_value.invoke.return_value = result


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@patch("triage.nodes.missing_info.llm")
def test_complete_issue_returns_no_missing_fields(mock_llm: MagicMock) -> None:
    """A complete issue should have is_complete=True and empty lists/strings."""
    patch_llm(
        mock_llm,
        MissingInfoResult(is_complete=True, missing_fields=[], draft_reply=""),
    )

    result = missing_info_node(make_state())

    assert result["is_complete"] is True
    assert result["missing_fields"] == []
    assert result["draft_reply"] == ""


@patch("triage.nodes.missing_info.llm")
def test_incomplete_issue_returns_missing_fields(mock_llm: MagicMock) -> None:
    """An incomplete issue should list what is missing."""
    patch_llm(
        mock_llm,
        MissingInfoResult(
            is_complete=False,
            missing_fields=["version", "steps to reproduce"],
            draft_reply="Could you share the version and steps to reproduce?",
        ),
    )

    result = missing_info_node(make_state())

    assert result["is_complete"] is False
    assert "version" in result["missing_fields"]
    assert "steps to reproduce" in result["missing_fields"]


@patch("triage.nodes.missing_info.llm")
def test_incomplete_issue_has_non_empty_draft_reply(mock_llm: MagicMock) -> None:
    """When information is missing the draft reply must be non-empty."""
    patch_llm(
        mock_llm,
        MissingInfoResult(
            is_complete=False,
            missing_fields=["error_message"],
            draft_reply="Could you share the error message or traceback?",
        ),
    )

    result = missing_info_node(make_state())

    assert isinstance(result["draft_reply"], str)
    assert len(result["draft_reply"]) > 0


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------


@patch("triage.nodes.missing_info.llm")
def test_node_returns_exactly_three_keys(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, MissingInfoResult(is_complete=True))

    result = missing_info_node(make_state())

    assert set(result.keys()) == {"is_complete", "missing_fields", "draft_reply"}


@patch("triage.nodes.missing_info.llm")
def test_missing_fields_is_always_a_list(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, MissingInfoResult(is_complete=True, missing_fields=[]))

    result = missing_info_node(make_state())

    assert isinstance(result["missing_fields"], list)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@patch("triage.nodes.missing_info.llm")
def test_node_wraps_llm_errors(mock_llm: MagicMock) -> None:
    mock_llm.with_structured_output.return_value.invoke.side_effect = Exception("timeout")

    with pytest.raises(RuntimeError, match="missing_info_node"):
        missing_info_node(make_state())
