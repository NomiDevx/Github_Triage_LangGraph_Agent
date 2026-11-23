"""
code_search agent node — step 3 of the triage graph for bugs.

Runs a tool-calling agent loop (search_code, read_file, list_directory)
over a local code directory to discover files most relevant to the bug report.
Hard step limit is enforced via recursion_limit.
Issue text is treated as untrusted input.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

try:
    from langchain.agents import create_agent
except ImportError:
    # Fallback to langgraph prebuilt if langchain.agents is not available
    from langgraph.prebuilt import create_react_agent as create_agent

from triage.config import settings
from triage.llm import llm
from triage.models import CodeSearchResult, TriageState
from triage.prompts import CODE_SEARCH_HUMAN, CODE_SEARCH_SYSTEM
from triage.tools import create_code_tools

logger = logging.getLogger(__name__)


def code_search_node(state: TriageState) -> dict[str, Any]:
    """LangGraph node: agentic code search to locate bug-related files."""
    title = state.get("issue_title", "")
    body = state.get("issue_body", "")
    raw_code_dir = state.get("code_dir")

    if not raw_code_dir:
        logger.info("code_search_node: no code_dir provided, skipping search")
        return {
            "likely_files": [],
            "summary": "No code directory provided for local file search.",
        }

    code_path = Path(raw_code_dir).resolve()
    if not code_path.exists() or not code_path.is_dir():
        logger.warning("code_search_node: code_dir '%s' is not a valid directory", code_path)
        return {
            "likely_files": [],
            "summary": f"Configured code directory '{raw_code_dir}' does not exist or is not a directory.",
        }

    logger.info("code_search_node: running code search agent over '%s' for '%s'", code_path, title)

    tools = create_code_tools(code_path)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=CODE_SEARCH_SYSTEM,
        response_format=CodeSearchResult,
    )

    human_prompt = CODE_SEARCH_HUMAN.format(title=title, body=body)
    # Each tool call loop takes ~2 graph steps (model call + tool call)
    recursion_limit = max(settings.max_code_search_steps * 2, 4)

    try:
        agent_output = agent.invoke(
            {"messages": [HumanMessage(content=human_prompt)]},
            config={"recursion_limit": recursion_limit},
        )
    except Exception as exc:
        logger.warning("code_search_node: agent run ended with error or step limit: %s", exc)
        return {
            "likely_files": [],
            "summary": f"Code search stopped before completion: {exc}",
        }

    structured = agent_output.get("structured_response")
    if isinstance(structured, CodeSearchResult):
        likely_files = structured.likely_files
        summary = structured.summary
    elif isinstance(structured, dict):
        likely_files = structured.get("likely_files", [])
        summary = structured.get("summary", "")
    else:
        # Fallback to content of the final AI message if response format was parsed loosely
        messages = agent_output.get("messages", [])
        last_content = messages[-1].content if messages else ""
        likely_files = []
        summary = str(last_content)

    # Clean and deduplicate paths
    cleaned_files: list[str] = []
    for f in likely_files:
        normalized = f.strip().replace("\\", "/")
        if normalized and normalized not in cleaned_files:
            cleaned_files.append(normalized)

    logger.info(
        "code_search_node: finished search, found %d likely files: %s",
        len(cleaned_files),
        cleaned_files,
    )

    return {
        "likely_files": cleaned_files,
        "summary": summary,
    }
