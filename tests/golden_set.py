#!/usr/bin/env python3
"""Deterministic golden-set checks for the governor's real gate functions."""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        import governor

        governor.DB_PATH = str(Path(directory) / "golden.db")
        governor.init_db()
        source = "The control plane records every request in a hash chained audit log."
        cases = [
            {"name": "noise-short", "block": "noise", "expected": False, "actual": governor.noise_gate("hi")},
            {"name": "noise-signal", "block": "noise", "expected": True, "actual": governor.noise_gate("explain audit records")},
            {"name": "loop-fourth", "block": "loop", "expected": False, "actual": [governor.loop_gate("agent", now) for now in (1, 2, 3, 4)][-1]},
            {"name": "quote-valid", "block": "citation", "expected": True, "actual": governor.citation_check('"The control plane records every request in a hash chained audit log."', [source])},
            {"name": "quote-invalid", "block": "citation", "expected": False, "actual": governor.citation_check('"A completely unrelated quoted sentence appears here."', [source])},
            {"name": "refusal-valid", "block": "citation", "expected": True, "actual": governor.citation_check(governor.REFUSAL, [])},
            {"name": "combined", "block": "combined", "expected": True, "actual": governor.noise_gate("summarize request history") and governor.citation_check("The control plane records every request", [source])},
        ]
        for case in cases:
            case["passed"] = case["actual"] == case["expected"]
        passed = sum(case["passed"] for case in cases)
        total = len(cases)
        false_positive = sum(case["actual"] and not case["expected"] for case in cases)
        false_negative = sum(not case["actual"] and case["expected"] for case in cases)
        precision = sum(case["actual"] and case["expected"] for case in cases) / max(sum(case["actual"] for case in cases), 1)
        recall = sum(case["actual"] and case["expected"] for case in cases) / max(sum(case["expected"] for case in cases), 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-12)
        return {"total": total, "passed": passed, "failed": total - passed, "precision": precision, "recall": recall, "f1": f1, "false_positive_rate": false_positive / total, "false_negative_rate": false_negative / total, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["failed"] == 0 else 1)