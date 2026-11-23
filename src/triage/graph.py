"""
Assembles and compiles the triage LangGraph.

Stage 4:
  classify → conditional edge:
    - bug            → missing_info → code_search → END
    - anything else  → END directly
"""

import logging

from langgraph.graph import END, START, StateGraph

from triage.models import TriageState
from triage.nodes.classify import classify_node
from triage.nodes.code_search import code_search_node
from triage.nodes.missing_info import missing_info_node

logger = logging.getLogger(__name__)

# The category value that triggers the bug triage pipeline.
_BUG_CATEGORY = "bug"


def _route_after_classify(state: TriageState) -> str:
    """Decides which node runs after classify.

    Returns 'missing_info' for bugs, which then proceeds to code_search.
    Non-bug issues bypass missing-info and code search, ending immediately.
    """
    if state.get("category") == _BUG_CATEGORY:
        return "missing_info"
    return END


def build_graph():
    """Builds and compiles the triage StateGraph."""
    workflow = StateGraph(TriageState)

    # --- nodes ---
    workflow.add_node("classify", classify_node)
    workflow.add_node("missing_info", missing_info_node)
    workflow.add_node("code_search", code_search_node)

    # --- edges ---
    workflow.add_edge(START, "classify")
    workflow.add_conditional_edges("classify", _route_after_classify)
    workflow.add_edge("missing_info", "code_search")
    workflow.add_edge("code_search", END)

    graph = workflow.compile()
    logger.info("graph: compiled triage graph (stage 4 — bug agentic code search enabled)")
    return graph


# Module-level compiled graph — imported by main.py and integration tests.
triage_graph = build_graph()
