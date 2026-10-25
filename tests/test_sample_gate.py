"""Public seam: the sample command must reproduce dataset/sample_output.csv."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ROOT / "build" / "sample_predictions.csv"
EXPECTED = ROOT / "dataset" / "sample_output.csv"


def _steps(payload: str) -> list[tuple[str, str, str, str, str, str]]:
    return [
        (
            step["phase"],
            step["operation"],
            step["state"],
            step["system_id"],
            step["resource_id"],
            step["evidence_id"],
        )
        for step in json.loads(payload)
    ]


class SampleGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = subprocess.run(
            [sys.executable, "code/main.py", "--samples"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_sample_command_matches_public_answers(self) -> None:
        self.assertTrue(PREDICTIONS.exists(), self.result.stderr + self.result.stdout)
        expected = {row["case_id"]: row for row in csv.DictReader(EXPECTED.open(encoding="utf-8"))}
        got = {row["case_id"]: row for row in csv.DictReader(PREDICTIONS.open(encoding="utf-8"))}
        self.assertEqual(set(expected), set(got), self.result.stdout)
        mismatches = []
        for case_id in sorted(expected, key=lambda item: int(item.split("_")[1])):
            gold = expected[case_id]
            row = got[case_id]
            if row["deletion_status"] != gold["deletion_status"] or _steps(row["steps_json"]) != _steps(gold["steps_json"]):
                mismatches.append(case_id)
        self.assertEqual(mismatches, [], self.result.stdout)
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)


if __name__ == "__main__":
    unittest.main()
