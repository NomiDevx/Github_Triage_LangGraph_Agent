"""
Pydantic output schemas and the shared LangGraph state.

Every LLM call returns one of the schemas defined here, so a bad model
response raises a ValidationError immediately rather than silently
propagating a half-parsed result to the next node.
"""

from __future__ import annotations

from enum import Enum
from typing import NotRequired, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class IssueCategory(str, Enum):
    """The four buckets an issue can fall into."""

    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    QUESTION = "question"
    DOCS = "docs"


# ---------------------------------------------------------------------------
# LLM output schemas  (one per node)
# ---------------------------------------------------------------------------


class ClassifyResult(BaseModel):
    """Structured output from the classify node LLM call."""

    category: IssueCategory = Field(
        description="The single best-fit category for this issue."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the model is, from 0.0 (wild guess) to 1.0 (certain).",
    )
    reasoning: str = Field(
        description="One sentence explaining the key signal that drove this classification."
    )


class MissingInfoResult(BaseModel):
    """Structured output from the missing-info node LLM call.  (Stage 2)"""

    is_complete: bool = Field(
        description="True when the issue contains enough information to act on."
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Human-readable names of the fields that are absent, e.g. ['version', 'steps to reproduce'].",
    )
    draft_reply: str = Field(
        default="",
        description=(
            "Polite reply asking for the missing information. "
            "Empty string when is_complete is True."
        ),
    )


class CodeSearchResult(BaseModel):
    """Structured output from the code-search agent. (Stage 4)"""

    likely_files: list[str] = Field(
        default_factory=list,
        description="Relative file paths in the codebase most likely related to the bug.",
    )
    summary: str = Field(
        default="",
        description="Short explanation of why these files are relevant and what was found.",
    )


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------


class TriageState(TypedDict):
    """The single state object that flows through every node in the graph.

    Fields are added by each node; earlier nodes leave later fields absent.
    Using NotRequired keeps the TypedDict strict about what is always present
    (issue_title, issue_body) versus what is set progressively.
    """

    # ---- always present (provided by the caller) ----
    issue_title: str
    issue_body: str

    # ---- optional caller input ----
    # Path to the local code folder; only needed when category == "bug".
    code_dir: NotRequired[str]

    # ---- set by classify node ----
    category: NotRequired[str]       # IssueCategory value as a plain string
    confidence: NotRequired[float]
    reasoning: NotRequired[str]

    # ---- set by missing_info node  (Stage 2) ----
    is_complete: NotRequired[bool]
    missing_fields: NotRequired[list[str]]
    draft_reply: NotRequired[str]

    # ---- set by code_search agent  (Stage 4) ----
    likely_files: NotRequired[list[str]]
    summary: NotRequired[str]
