#!/usr/bin/env python3
"""Deterministic golden-set checks for the governor's gate functions."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

# These thresholds mirror the current governor.py defaults and are exported in the
# JSON artifact so future readers can audit exactly what the suite is testing.
NOISE_MIN_WORDS = 3
NOISE_MIN_CHARS = 8
NOISE_MIN_UNIQUE_WORDS = 2
LOOP_WINDOW_SECONDS = 300
LOOP_MAX_EVENTS = 3
QUOTE_MIN_OVERLAP = 0.90
PROSE_MIN_OVERLAP = 0.35

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(1 for case in cases if case["expected"] and case["actual"])
    tn = sum(1 for case in cases if not case["expected"] and not case["actual"])
    fp = sum(1 for case in cases if case["actual"] and not case["expected"])
    fn = sum(1 for case in cases if not case["actual"] and case["expected"])
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    fails = [case["name"] for case in cases if case["actual"] != case["expected"]]
    return {
        "n": len(cases),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fp / len(cases) if cases else 0.0,
        "false_negative_rate": fn / len(cases) if cases else 0.0,
        "fails": fails,
        "cases": cases,
    }


def _evaluate_block(block_name: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    for case in cases:
        case["block"] = block_name
        case["passed"] = bool(case["actual"] == case["expected"])
    return _metrics(cases)


def build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as directory:
        import governor

        governor.DB_PATH = str(Path(directory) / "golden.db")
        governor.init_db()

        source = "The control plane records every request in a hash chained audit log."
        source_quote = '"The control plane records every request in a hash chained audit log."'
        source_alternate = "The control plane keeps every request in a hash-chained audit log."
        noise_cases = [
            {"name": "noise-short", "expected": False, "actual": governor.noise_gate("hi")},
            {"name": "noise-signal", "expected": True, "actual": governor.noise_gate("explain audit records")},
            {"name": "noise-very-short", "expected": False, "actual": governor.noise_gate("x x")},
            {"name": "noise-numeric-only", "expected": False, "actual": governor.noise_gate("12345")},
            {"name": "noise-mixed", "expected": True, "actual": governor.noise_gate("Explain the audit trail")},
            {"name": "noise-casefold", "expected": True, "actual": governor.noise_gate("EXPLAIN request logs")},
            {"name": "noise-stopwordish", "expected": True, "actual": governor.noise_gate("run data model logs")},
            {"name": "noise-duplicate", "expected": False, "actual": governor.noise_gate("audit audit audit")},
            {"name": "noise-long", "expected": True, "actual": governor.noise_gate("track all retrieval provenance and audit chains")},
        ]

        loop_cases = []
        for now in (1, 2, 3):
            loop_cases.append({"name": f"loop-{now}", "expected": True, "actual": governor.loop_gate("agent-a", now)})
        loop_cases.append({"name": "loop-fourth", "expected": False, "actual": governor.loop_gate("agent-a", 4)})
        loop_cases.append({"name": "loop-stale-reset", "expected": True, "actual": governor.loop_gate("agent-a", 401)})
        loop_cases.append({"name": "loop-other-agent", "expected": True, "actual": governor.loop_gate("agent-b", 500)})

        citation_cases = [
            {"name": "quote-valid", "expected": True, "actual": governor.citation_check(source_quote, [source])},
            {"name": "quote-invalid", "expected": False, "actual": governor.citation_check('"A completely unrelated quoted sentence appears here."', [source])},
            {"name": "refusal-valid", "expected": True, "actual": governor.citation_check(governor.REFUSAL, [])},
            {"name": "refusal-invalid", "expected": False, "actual": governor.citation_check("I cannot answer from the supplied sources!", [])},
            {"name": "prose-valid", "expected": True, "actual": governor.citation_check(source_alternate, [source])},
            {"name": "prose-invalid", "expected": False, "actual": governor.citation_check("A recipe for making soup in twenty minutes.", [source])},
            {"name": "multiple-quotes-valid", "expected": True, "actual": governor.citation_check('"The control plane records every request in a hash chained audit log." "The control plane records every request in a hash chained audit log."', [source])},
            {"name": "multiple-quotes-invalid", "expected": False, "actual": governor.citation_check('"The control plane records every request in a hash chained audit log." "Completely unrelated quoted content appears here."', [source])},
            {"name": "cite_fabricated_number", "expected": False, "actual": governor.citation_check('"The control plane records 42 requests in a hash chained audit log."', [source])},
            {"name": "empty-source-fails", "expected": False, "actual": governor.citation_check("The control plane records every request in a hash chained audit log.", [])},
            {"name": "short-quote-valid", "expected": True, "actual": governor.citation_check('"records every request in a hash chained audit log"', [source])},
            {"name": "paraphrase-low-overlap", "expected": False, "actual": governor.citation_check("A kitchen gadget for making tea and bread.", [source])},
        ]

        noise_result = _evaluate_block("noise", noise_cases)
        loop_result = _evaluate_block("loop", loop_cases)
        citation_result = _evaluate_block("citation", citation_cases)
        combined_cases = noise_cases + loop_cases + citation_cases
        combined_result = _evaluate_block("combined", combined_cases)

        return {
            "config": {
                "name": "governor-golden-set",
                "thresholds": {
                    "noise_gate_min_words": NOISE_MIN_WORDS,
                    "noise_gate_min_chars": NOISE_MIN_CHARS,
                    "noise_gate_min_unique_words": NOISE_MIN_UNIQUE_WORDS,
                    "loop_window_seconds": LOOP_WINDOW_SECONDS,
                    "loop_max_events": LOOP_MAX_EVENTS,
                    "quote_overlap": QUOTE_MIN_OVERLAP,
                    "prose_overlap": PROSE_MIN_OVERLAP,
                },
                "total_cases": len(combined_cases),
            },
            "noise": noise_result,
            "loop": loop_result,
            "citation": citation_result,
            "combined": combined_result,
        }


def _print_section(title: str, result: dict[str, Any]) -> None:
    print(f"{title}")
    print(f"  n: {result['n']}")
    print(f"  tp: {result['tp']}  fp: {result['fp']}  tn: {result['tn']}  fn: {result['fn']}")
    print(f"  precision: {result['precision']:.3f}")
    print(f"  recall: {result['recall']:.3f}")
    print(f"  f1: {result['f1']:.3f}")
    print(f"  false_positive_rate: {result['false_positive_rate']:.3f}")
    print(f"  false_negative_rate: {result['false_negative_rate']:.3f}")
    print(f"  fails: {result['fails']}")
    print("  cases:")
    for case in result["cases"]:
        print(f"    - {case['name']}: expected={case['expected']}, actual={case['actual']}, passed={case['passed']}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the deterministic golden-set validation for the governor.")
    parser.add_argument("--json", type=Path, help="Optional path to write the JSON summary report.")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")

    print("GOVERNOR GOLDEN SET")
    print("==================")
    print("THRESHOLDS")
    print(f"  noise_min_words={NOISE_MIN_WORDS}")
    print(f"  noise_min_chars={NOISE_MIN_CHARS}")
    print(f"  noise_min_unique_words={NOISE_MIN_UNIQUE_WORDS}")
    print(f"  loop_window_seconds={LOOP_WINDOW_SECONDS}")
    print(f"  loop_max_events={LOOP_MAX_EVENTS}")
    print(f"  quote_min_overlap={QUOTE_MIN_OVERLAP}")
    print(f"  prose_min_overlap={PROSE_MIN_OVERLAP}")
    print()
    _print_section("NOISE GATE", report["noise"])
    _print_section("LOOP GATE", report["loop"])
    _print_section("CITATION CHECK", report["citation"])
    _print_section("SUMMARY", report["combined"])

    failed = report["combined"]["n"] - report["combined"]["tp"] - report["combined"]["tn"]
    raise SystemExit(0 if failed == 0 else 1)