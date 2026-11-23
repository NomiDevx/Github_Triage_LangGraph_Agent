"""
Builds the shared DeepSeek LLM client.

One place to construct the model so that every node uses the same
configuration and so that tests can patch a single import target.
"""

import logging

from langchain_deepseek import ChatDeepSeek

from triage.config import get_deepseek_api_key, settings

logger = logging.getLogger(__name__)


def build_llm() -> ChatDeepSeek:
    """Instantiates the ChatDeepSeek model with settings from config.

    The API key check is explicit here (not silently swallowed) so that a
    missing key causes a clear error at startup, not a cryptic 401 later.
    """
    api_key = get_deepseek_api_key()
    logger.debug("Building LLM: model=%s temperature=%s", settings.model_name, settings.model_temperature)
    return ChatDeepSeek(
        model=settings.model_name,
        temperature=settings.model_temperature,
        api_key=api_key,
    )


# Module-level singleton — constructed once, shared across all nodes.
llm = build_llm()
