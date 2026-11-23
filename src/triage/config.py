"""
Runtime configuration for the triage system.

All magic numbers and tunable knobs live here — nowhere else.
Importing this module is safe even without a real API key; the key
is retrieved lazily by get_deepseek_api_key() so tests can patch it.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable bag of settings loaded from the environment.

    Frozen so that nothing accidentally mutates global config at runtime.
    """

    model_name: str = "deepseek-chat"
    model_temperature: float = 0.0

    # Code-search agent: LangGraph raises GraphRecursionError beyond this.
    # Each LLM call + each tool call counts as one step, so 10 ≈ 5 round-trips.
    max_code_search_steps: int = 10

    # Prevents the model spending its whole context window on one large file.
    max_file_read_chars: int = 8_000

    # Cap on paths returned by search_code() per query.
    max_search_results: int = 10

    # Patterns and names always skipped by directory listings and code search.
    ignored_names: tuple[str, ...] = (
        ".git",
        ".env",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    )


settings = Settings()


def get_deepseek_api_key() -> str:
    """Returns the DeepSeek API key, raising clearly if it is absent.

    Kept separate from Settings so that importing config in tests does not
    require a real key in the environment.
    """
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError(
            "DEEPSEEK_API_KEY is not set. "
            "Copy .env.example to .env and fill in your key."
        )
    return key
