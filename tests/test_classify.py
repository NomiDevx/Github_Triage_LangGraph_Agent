"""
Unit tests for the classify node.

The LLM is mocked throughout — these tests verify that classify_node()
correctly packages the model's response into the expected state dict shape,
handles all four categories, and re-raises LLM errors with context.
"""

from unittest.mock import MagicMock, patch

import pytest

from triage.models import ClassifyResult, IssueCategory, TriageState
from triage.nodes.classify import classify_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(title: str, body: str) -> TriageState:
    """Minimal valid TriageState for testing the classify node."""
    return {"issue_title": title, "issue_body": body}


def make_classify_result(
    category: IssueCategory,
    confidence: float = 0.9,
    reasoning: str = "Test reasoning.",
) -> ClassifyResult:
    return ClassifyResult(category=category, confidence=confidence, reasoning=reasoning)


def patch_llm(mock_llm: MagicMock, result: ClassifyResult) -> None:
    """Wires mock_llm.with_structured_output(...).invoke(...) to return result."""
    mock_llm.with_structured_output.return_value.invoke.return_value = result


# ---------------------------------------------------------------------------
# Category tests
# ---------------------------------------------------------------------------


@patch("triage.nodes.classify.llm")
def test_classify_bug(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, make_classify_result(IssueCategory.BUG, confidence=0.95))

    result = classify_node(make_state("App crashes on startup", "NullPointerException on line 42."))

    assert result["category"] == "bug"
    assert result["confidence"] == 0.95


@patch("triage.nodes.classify.llm")
def test_classify_feature_request(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, make_classify_result(IssueCategory.FEATURE_REQUEST, confidence=0.88))

    result = classify_node(make_state("Add dark mode", "It would be great to have dark mode."))

    assert result["category"] == "feature_request"
    assert result["confidence"] == 0.88


@patch("triage.nodes.classify.llm")
def test_classify_question(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, make_classify_result(IssueCategory.QUESTION, confidence=0.80))

    result = classify_node(make_state("How do I configure X?", "I cannot figure out the config."))

    assert result["category"] == "question"


@patch("triage.nodes.classify.llm")
def test_classify_docs(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, make_classify_result(IssueCategory.DOCS, confidence=0.85))

    result = classify_node(make_state("Missing docs for --verbose", "README doesn't mention it."))

    assert result["category"] == "docs"


# ---------------------------------------------------------------------------
# Output shape tests
# ---------------------------------------------------------------------------


@patch("triage.nodes.classify.llm")
def test_classify_returns_exactly_three_keys(mock_llm: MagicMock) -> None:
    """Node must return exactly the keys that map to TriageState fields."""
    patch_llm(mock_llm, make_classify_result(IssueCategory.BUG))

    result = classify_node(make_state("title", "body"))

    assert set(result.keys()) == {"category", "confidence", "reasoning"}


@patch("triage.nodes.classify.llm")
def test_classify_category_is_plain_string(mock_llm: MagicMock) -> None:
    """category must be a str value like 'bug', not an IssueCategory enum."""
    patch_llm(mock_llm, make_classify_result(IssueCategory.FEATURE_REQUEST))

    result = classify_node(make_state("title", "body"))

    assert isinstance(result["category"], str)
    assert result["category"] == "feature_request"


@patch("triage.nodes.classify.llm")
def test_classify_confidence_is_float(mock_llm: MagicMock) -> None:
    patch_llm(mock_llm, make_classify_result(IssueCategory.BUG, confidence=0.72))

    result = classify_node(make_state("title", "body"))

    assert isinstance(result["confidence"], float)
    assert result["confidence"] == pytest.approx(0.72)


@patch("triage.nodes.classify.llm")
def test_classify_reasoning_is_string(mock_llm: MagicMock) -> None:
    patch_llm(
        mock_llm,
        make_classify_result(IssueCategory.QUESTION, reasoning="User is asking for help."),
    )

    result = classify_node(make_state("title", "body"))

    assert isinstance(result["reasoning"], str)
    assert result["reasoning"] == "User is asking for help."


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@patch("triage.nodes.classify.llm")
def test_classify_wraps_llm_errors(mock_llm: MagicMock) -> None:
    """LLM failures should bubble up as RuntimeError with context."""
    mock_llm.with_structured_output.return_value.invoke.side_effect = Exception("API timeout")

    with pytest.raises(RuntimeError, match="classify_node"):
        classify_node(make_state("title", "body"))
