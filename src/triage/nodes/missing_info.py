"""
missing_info node — step 2 of the triage graph.

Checks whether a bug report contains the three fields we need to act on it:
  - version of the software
  - steps to reproduce
  - error message / logs

If anything is missing, it drafts a polite reply asking only for those items.
We only run this node for bugs; feature requests and questions don't need it
(the conditional edge in graph.py handles that routing).
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from triage.llm import llm
from triage.models import MissingInfoResult, TriageState
from triage.prompts import MISSING_INFO_HUMAN, MISSING_INFO_SYSTEM

logger = logging.getLogger(__name__)


def missing_info_node(state: TriageState) -> dict:
    """LangGraph node: check completeness of a bug report and draft a reply.

    Returns a partial state dict with is_complete, missing_fields, and
    draft_reply.  For non-bug issues these fields stay absent in state
    because the conditional edge skips this node entirely.
    """
    title = state["issue_title"]
    body = state["issue_body"]

    logger.info("missing_info_node: checking completeness for '%s'", title)

    messages = [
        SystemMessage(content=MISSING_INFO_SYSTEM),
        HumanMessage(content=MISSING_INFO_HUMAN.format(title=title, body=body)),
    ]

    structured_llm = llm.with_structured_output(MissingInfoResult)

    try:
        result: MissingInfoResult = structured_llm.invoke(messages)
    except Exception as exc:
        raise RuntimeError(
            f"missing_info_node: LLM call failed for issue '{title}': {exc}"
        ) from exc

    if result.is_complete:
        logger.info("missing_info_node: issue is complete — no reply needed")
    else:
        logger.info(
            "missing_info_node: missing fields: %s",
            result.missing_fields,
        )

    return {
        "is_complete": result.is_complete,
        "missing_fields": result.missing_fields,
        "draft_reply": result.draft_reply,
    }
