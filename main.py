"""
CLI entry point.

Usage:
    python main.py sample_issues/bug_example.txt
    python main.py sample_issues/bug_example.txt --code-dir path/to/code

The issue file format:
    Line 1   : issue title
    Lines 2+ : issue body
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src/ to the path so that `import triage` works when running this script
# directly from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from triage.graph import triage_graph  # noqa: E402  (import after sys.path patch)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Triage a GitHub issue and suggest a category and reply."
    )
    parser.add_argument(
        "issue_file",
        nargs="?",
        default=None,
        type=Path,
        help="Path to a text file: first line = title, remaining lines = body.",
    )
    parser.add_argument(
        "--code-dir",
        type=Path,
        default=None,
        help="Local code folder to search when the issue is classified as a bug (Stage 4).",
    )
    parser.add_argument(
        "--stdin-json",
        action="store_true",
        help="Read JSON payload from stdin with keys: title, body, and optional code_dir.",
    )
    return parser.parse_args()


def load_issue(issue_file: Path) -> tuple[str, str]:
    """Reads an issue text file and splits it into title and body.

    The first non-empty line is treated as the title; everything else is body.
    This matches how issues are pasted into a plain text file.
    """
    text = issue_file.read_text(encoding="utf-8").strip()
    lines = text.splitlines()
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    return title, body


def build_output(result: dict) -> dict:
    """Extracts the fields we care about from the final graph state.

    Keeping this separate makes it easy to extend as more nodes are added.
    None means the field was not populated (e.g. missing_info skipped for
    non-bug issues); consumers should treat None and [] as "not applicable".
    """
    return {
        "category": result.get("category"),
        "confidence": result.get("confidence"),
        "reasoning": result.get("reasoning"),
        # Stage 2: only populated for bugs; None for other categories.
        "is_complete": result.get("is_complete"),
        "missing_fields": result.get("missing_fields"),
        "draft_reply": result.get("draft_reply"),
        # Stage 4: code search results (populated for bugs when code_dir provided).
        "likely_files": result.get("likely_files", []),
        "summary": result.get("summary", ""),
    }


def main() -> None:
    args = parse_args()

    if args.stdin_json:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            logger.error("Empty stdin provided with --stdin-json")
            sys.exit(1)
        payload = json.loads(raw_input)
        title = payload.get("title", "").strip()
        body = payload.get("body", "").strip()
        code_dir_arg = payload.get("code_dir") or args.code_dir
    else:
        if not args.issue_file:
            logger.error("Please provide an issue_file or use --stdin-json")
            sys.exit(1)
        if not args.issue_file.exists():
            logger.error("Issue file not found: %s", args.issue_file)
            sys.exit(1)
        title, body = load_issue(args.issue_file)
        code_dir_arg = args.code_dir

    logger.info("Loaded issue: '%s'", title)

    initial_state: dict = {
        "issue_title": title,
        "issue_body": body,
    }
    if code_dir_arg:
        initial_state["code_dir"] = str(Path(code_dir_arg).resolve())

    logger.info("Running triage graph...")
    result = triage_graph.invoke(initial_state)

    output = build_output(result)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
