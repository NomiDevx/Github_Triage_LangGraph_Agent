"""
Assembles and compiles the triage LangGraph.

Stage 1 contains only the classify node.
Later stages add missing_info, code_search, and conditional edges here
without touching any node files.
"""

import logging

from langgraph.graph import END, START, StateGraph

from triage.models import TriageState
from triage.nodes.classify import classify_node

logger = logging.getLogger(__name__)


def build_graph():
    """Builds the triage workflow as a LangGraph StateGraph.

    Keeping build_graph() as a function (rather than top-level code) means
    tests can call it directly and get a fresh graph without import-time
    side effects.
    """
    workflow = StateGraph(TriageState)

    # --- nodes ---
    workflow.add_node("classify", classify_node)

    # --- edges ---
    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", END)

    graph = workflow.compile()
    logger.info("graph: compiled triage graph (stage 1 — classify only)")
    return graph


# Module-level compiled graph — imported by main.py and by integration tests.
triage_graph = build_graph()
