"""
Evaluation runner for the GitHub issue triage system.

Runs every labeled issue in evals/dataset.jsonl through the triage pipeline,
measures classification accuracy, and prints a formatted confusion summary.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --dataset evals/dataset.jsonl --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add src/ to sys.path so triage package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv()

from triage.graph import triage_graph
from triage.models import IssueCategory

# Quiet down HTTP request logs during evaluation run unless debugging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpx2").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("triage").setLevel(logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run triage accuracy evaluation.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "evals" / "dataset.jsonl",
        help="Path to labeled evaluation dataset in JSONL format.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed model reasoning for each evaluated case.",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Emit full results as JSON to stdout for programmatic and UI integration.",
    )
    return parser.parse_args()


def load_dataset(dataset_path: Path) -> list[dict]:
    """Loads JSONL dataset records."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

    records = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSON on line {line_num} of {dataset_path}: {exc}") from exc
    return records


def print_confusion_matrix(
    categories: list[str],
    confusion: dict[str, dict[str, int]],
) -> None:
    """Prints a formatted 2D confusion matrix."""
    header = f"{'Expected \\ Pred':<18} " + " ".join(f"{cat:>15}" for cat in categories)
    print("\n" + "=" * len(header))
    print("Confusion Matrix")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for actual in categories:
        row_str = f"{actual:<18} "
        for pred in categories:
            count = confusion[actual][pred]
            row_str += f"{count:>15} "
        print(row_str)
    print("=" * len(header) + "\n")


def run_evaluation(
    dataset: list[dict],
    verbose: bool = False,
    json_output: bool = False,
) -> float:
    """Runs each sample through the triage pipeline and computes accuracy metrics."""
    categories = [cat.value for cat in IssueCategory]
    confusion: dict[str, dict[str, int]] = {
        act: {pred: 0 for pred in categories} for act in categories
    }

    correct_classifications = 0
    total_samples = len(dataset)
    completeness_evals: list[bool] = []
    sample_records: list[dict] = []

    if not json_output:
        print(f"\nRunning triage evaluation on {total_samples} samples from dataset...\n")
        print(f"{'ID':<4} {'Expected':<16} {'Predicted':<16} {'Conf':<6} {'Match':<6} {'Title'}")
        print("-" * 80)

    start_time = time.perf_counter()

    for item in dataset:
        item_id = item.get("id", "-")
        title = item["title"]
        body = item["body"]
        expected_cat = item["expected_category"]
        expected_is_complete = item.get("expected_is_complete")

        initial_state = {
            "issue_title": title,
            "issue_body": body,
        }

        try:
            result = triage_graph.invoke(initial_state)
            predicted_cat = result.get("category", "unknown")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            is_complete = result.get("is_complete")
        except Exception as exc:
            predicted_cat = "error"
            confidence = 0.0
            reasoning = str(exc)
            is_complete = None

        is_match = (predicted_cat == expected_cat)
        if is_match:
            correct_classifications += 1

        if expected_cat in confusion and predicted_cat in confusion[expected_cat]:
            confusion[expected_cat][predicted_cat] += 1

        if expected_is_complete is not None and is_complete is not None:
            completeness_evals.append(is_complete == expected_is_complete)

        sample_records.append({
            "id": item_id,
            "title": title,
            "expected_category": expected_cat,
            "predicted_category": predicted_cat,
            "confidence": confidence,
            "reasoning": reasoning,
            "is_complete": is_complete,
            "expected_is_complete": expected_is_complete,
            "match": is_match,
        })

        if not json_output:
            status_symbol = "PASS" if is_match else "FAIL"
            short_title = title[:35] + ("..." if len(title) > 35 else "")
            print(
                f"{item_id:<4} {expected_cat:<16} {predicted_cat:<16} {confidence:<6.2f} "
                f"{status_symbol:<6} {short_title}"
            )

            if verbose:
                print(f"     Reasoning: {reasoning}")
                if result.get("missing_fields"):
                    print(f"     Missing: {result['missing_fields']}")
                if result.get("draft_reply"):
                    print(f"     Reply: {result['draft_reply']}")
                print()

    total_time = time.perf_counter() - start_time
    accuracy = (correct_classifications / total_samples) * 100 if total_samples > 0 else 0.0

    if json_output:
        payload = {
            "total_samples": total_samples,
            "correct_classifications": correct_classifications,
            "accuracy": round(accuracy, 1),
            "total_time_seconds": round(total_time, 2),
            "categories": categories,
            "confusion_matrix": confusion,
            "samples": sample_records,
            "completeness_accuracy": (
                round((sum(completeness_evals) / len(completeness_evals)) * 100, 1)
                if completeness_evals
                else None
            ),
        }
        print(json.dumps(payload))
        return accuracy

    print("-" * 80)
    print(f"\nCompleted {total_samples} samples in {total_time:.2f}s ({total_time / total_samples:.2f}s/sample)")
    print(f"Overall Classification Accuracy: {correct_classifications}/{total_samples} ({accuracy:.1f}%)")

    print("\nPer-Category Breakdown:")
    for cat in categories:
        total_for_cat = sum(confusion[cat].values())
        correct_for_cat = confusion[cat][cat]
        cat_acc = (correct_for_cat / total_for_cat * 100) if total_for_cat > 0 else 0.0
        print(f"  - {cat:<16}: {correct_for_cat}/{total_for_cat} ({cat_acc:.1f}%)")

    if completeness_evals:
        comp_acc = (sum(completeness_evals) / len(completeness_evals)) * 100
        print(f"\nBug Completeness Check Accuracy: {sum(completeness_evals)}/{len(completeness_evals)} ({comp_acc:.1f}%)")

    print_confusion_matrix(categories, confusion)
    return accuracy


def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.dataset)
    accuracy = run_evaluation(
        dataset,
        verbose=args.verbose,
        json_output=args.json_output,
    )
    if not args.json_output and accuracy < 80.0:
        print(f"Warning: Accuracy ({accuracy:.1f}%) is below 80% baseline threshold.")
        sys.exit(1)


if __name__ == "__main__":
    main()
