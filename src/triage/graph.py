"""
Assembles and compiles the triage LangGraph.

Stage 2: classify → conditional edge → missing_info (bugs only) → END.

The conditional edge means:
  - bug            → missing_info node (checks completeness, drafts reply)
  - anything else  → END directly (no completeness check needed)
"""

import logging

from langgraph.graph import END, START, StateGraph

from triage.models import TriageState
from triage.nodes.classify import classify_node
from triage.nodes.missing_info import missing_info_node

logger = logging.getLogger(__name__)

# The category value that triggers the missing-info check.
_BUG_CATEGORY = "bug"


def _route_after_classify(state: TriageState) -> str:
    """Decides which node runs after classify.

    Returns the node name (or END) based on the category set by classify_node.
    Using a named function (rather than a lambda) keeps the graph readable
    when LangGraph prints its structure.
    """
    if state.get("category") == _BUG_CATEGORY:
        return "missing_info"
    return END


def build_graph():
    """Builds and compiles the triage StateGraph.

    Keeping this as a function (not top-level code) lets tests call it
    directly to get a fresh graph without worrying about import-time side
    effects.
    """
    workflow = StateGraph(TriageState)

    # --- nodes ---
    workflow.add_node("classify", classify_node)
    workflow.add_node("missing_info", missing_info_node)

    # --- edges ---
    workflow.add_edge(START, "classify")
    workflow.add_conditional_edges("classify", _route_after_classify)
    workflow.add_edge("missing_info", END)

    graph = workflow.compile()
    logger.info(
        "graph: compiled triage graph (stage 2 — classify + missing_info for bugs)"
    )
    return graph


# Module-level compiled graph — imported by main.py and integration tests.
triage_graph = build_graph()
