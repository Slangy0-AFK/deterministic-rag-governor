import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.golden_set import build_report


def test_governor_golden_set() -> None:
    report = build_report()

    assert report["config"]["total_cases"] == 27
    assert report["combined"]["n"] == 27
    assert report["combined"]["tp"] == 15
    assert report["combined"]["tn"] == 12
    assert report["combined"]["fp"] == 0
    assert report["combined"]["fn"] == 0
    assert report["combined"]["precision"] == 1.0
    assert report["combined"]["recall"] == 1.0
    assert report["combined"]["f1"] == 1.0
    assert report["combined"]["fails"] == []

    report_path = Path(__file__).resolve().parents[1] / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    assert report_path.exists()
