"""Run the deletion-audit pipeline.

The full run writes root output.csv only when every case decides without a
guess. --samples scores the 32 public cases and writes build/sample_predictions.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classify import is_deletion_request
from decide import STEP_KEYS, decide_case
from evidence_index import build_index
from identity import load_identities

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ghost Data Still Exists deletion audit")
    parser.add_argument("--samples", action="store_true", help="Score the 32 public cases")
    args = parser.parse_args()
    if args.samples:
        return run_samples()
    return run_full()


def run_samples() -> int:
    requests = _read_csv(DATASET / "sample_deletion_requests.csv")
    expected = {row["case_id"]: row for row in _read_csv(DATASET / "sample_output.csv")}
    results, blockers = _evaluate(requests)
    out = ROOT / "build" / "sample_predictions.csv"
    _write(out, results)
    status_hits = 0
    step_hits = 0
    for row in results:
        gold = expected[row["case_id"]]
        if row["deletion_status"] == gold["deletion_status"]:
            status_hits += 1
        if _step_tuples(row["steps_json"]) == _step_tuples(gold["steps_json"]):
            step_hits += 1
    print(f"status {status_hits}/{len(results)}  steps {step_hits}/{len(results)}  blocked {len(blockers)}")
    for case_id, reasons in list(blockers.items())[:12]:
        print(f"blocked {case_id}: {reasons[0]}")
    for row in results:
        gold = expected[row["case_id"]]
        if row["deletion_status"] != gold["deletion_status"]:
            print(f"status mismatch {row['case_id']}: got {row['deletion_status'] or 'BLOCKED'} expected {gold['deletion_status']}")
    return 0


def run_full() -> int:
    requests = _read_csv(DATASET / "deletion_requests.csv")
    results, blockers = _evaluate(requests)
    if blockers or len(results) != len(requests):
        print(f"refusing to write output.csv: {len(blockers)} cases have no grounded decision", file=sys.stderr)
        for case_id, reasons in list(blockers.items())[:20]:
            print(f"blocked {case_id}: {reasons[0]}", file=sys.stderr)
        return 1
    _write(ROOT / "output.csv", results)
    print(f"wrote {len(results)} rows to output.csv")
    return 0


def _evaluate(requests: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    identities = load_identities(DATASET)
    observations, links = build_index(DATASET)
    results = []
    blockers: dict[str, list[str]] = {}
    for request in requests:
        decision = is_deletion_request(request["request_text"])
        if decision is None:
            blockers[request["case_id"]] = ["unmatched request text"]
            continue
        if not decision:
            results.append({"case_id": request["case_id"], "deletion_status": "NOT_APPLICABLE", "steps_json": "[]"})
            continue
        subject = identities.resolve(request["email"])
        if subject is None:
            blockers[request["case_id"]] = ["email did not resolve"]
            continue
        outcome = decide_case(request["audit_at"], subject, observations, links)
        if outcome.blockers or not outcome.status:
            blockers[request["case_id"]] = outcome.blockers or ["no decision"]
            continue
        results.append(
            {
                "case_id": request["case_id"],
                "deletion_status": outcome.status,
                "steps_json": json.dumps(outcome.steps, ensure_ascii=True, separators=(",", ":")),
            }
        )
    results.sort(key=lambda row: int(row["case_id"].split("_")[1]))
    return results, blockers


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "deletion_status", "steps_json"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _step_tuples(payload: str) -> list[tuple[str, str, str, str, str, str]]:
    steps = json.loads(payload)
    return [
        (step["phase"], step["operation"], step["state"], step["system_id"], step["resource_id"], step["evidence_id"])
        for step in steps
    ]


if __name__ == "__main__":
    raise SystemExit(main())
