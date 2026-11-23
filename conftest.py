"""
pytest configuration for the triage project.

This file runs before any test is imported, which lets us:
1. Add src/ to the Python path so tests can do `from triage.xxx import yyy`.
2. Set a fake API key so that importing triage.llm (which checks for the key)
   does not blow up in a CI environment that has no real key.
   The LLM is always mocked in unit tests, so the fake key is never sent.
"""

import os
import sys
from pathlib import Path

# Must come before any triage.* import.
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-fake-key-for-unit-tests")

sys.path.insert(0, str(Path(__file__).parent / "src"))
