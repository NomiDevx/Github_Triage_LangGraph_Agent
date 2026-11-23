"""
classify node — step 1 of the triage graph.

Sends the issue title + body to the LLM and gets back a category,
confidence score, and one-sentence reasoning. Using with_structured_output
means a malformed model response raises immediately (ValidationError)
rather than silently producing wrong data downstream.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from triage.llm import llm
from triage.models import ClassifyResult, TriageState
from triage.prompts import CLASSIFY_HUMAN, CLASSIFY_SYSTEM

logger = logging.getLogger(__name__)


def classify_node(state: TriageState) -> dict:
    """LangGraph node: classify the issue into one of four categories.

    Returns a partial state dict; LangGraph merges it into the full state.
    """
    title = state["issue_title"]
    body = state["issue_body"]

    logger.info("classify_node: classifying issue '%s'", title)

    messages = [
        SystemMessage(content=CLASSIFY_SYSTEM),
        HumanMessage(content=CLASSIFY_HUMAN.format(title=title, body=body)),
    ]

    structured_llm = llm.with_structured_output(ClassifyResult)

    try:
        result: ClassifyResult = structured_llm.invoke(messages)
    except Exception as exc:
        # Re-raise with enough context to debug without reading source.
        raise RuntimeError(
            f"classify_node: LLM call failed for issue '{title}': {exc}"
        ) from exc

    logger.info(
        "classify_node: category=%s confidence=%.2f | %s",
        result.category.value,
        result.confidence,
        result.reasoning,
    )

    return {
        "category": result.category.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }
