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

from agent import ExtractionError, FactAgent
from classify import is_deletion_request
from decide import decide_case
from evidence_index import build_index
from identity import load_identities

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
LAST_AGENT: FactAgent | None = None


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
    results, blockers = _evaluate(requests, require_vision=False)
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
    matched = status_hits == len(expected) and step_hits == len(expected) and not blockers and len(results) == len(expected)
    _write_usage(ROOT / "code" / "evaluation" / "usage_report.md", "sample gate")
    return 0 if matched else 1


def run_full() -> int:
    requests = _read_csv(DATASET / "deletion_requests.csv")
    results, blockers = _evaluate(requests, require_vision=True)
    seen = {row["case_id"] for row in results}
    for case_id, reasons in blockers.items():
        if case_id in seen:
            continue
        print(f"no eligible evidence for {case_id}: {reasons[0]}; writing COMPLETE with no steps", file=sys.stderr)
        results.append({"case_id": case_id, "deletion_status": "COMPLETE", "steps_json": "[]"})
    results.sort(key=lambda row: int(row["case_id"].split("_")[1]))
    if len(results) != len(requests):
        print(f"refusing to write output.csv: {len(requests) - len(results)} cases missing", file=sys.stderr)
        return 1
    _write(ROOT / "output.csv", results)
    _write_usage(ROOT / "code" / "evaluation" / "usage_report.md", "full dataset")
    print(f"wrote {len(results)} rows to output.csv")
    return 0


def _evaluate(requests: list[dict[str, str]], require_vision: bool) -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    global LAST_AGENT
    identities = load_identities(DATASET)
    agent = FactAgent.from_env(ROOT / "build" / "extraction_cache.sqlite")
    LAST_AGENT = agent
    try:
        observations, links = build_index(DATASET, agent)
    except ExtractionError as exc:
        return [], {request["case_id"]: [str(exc)] for request in requests[:1]} or {"run": [str(exc)]}
    results = []
    blockers: dict[str, list[str]] = {}
    if agent.vision_skipped and require_vision:
        print(
            f"warning: vision skipped for {len(agent.vision_skipped)} files; continuing with text evidence",
            file=sys.stderr,
        )
    for request in requests:
        decision = is_deletion_request(request["request_text"])
        if decision is None:
            try:
                decision = agent.classify(request["request_text"])
            except ExtractionError as exc:
                blockers[request["case_id"]] = [str(exc)]
                continue
        if decision is None:
            results.append({"case_id": request["case_id"], "deletion_status": "NOT_APPLICABLE", "steps_json": "[]"})
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


def _write_usage(path: Path, label: str) -> None:
    agent = LAST_AGENT
    lines = [
        "# Token usage",
        "",
        f"Run: {label}",
        "",
        "The policy engine chooses `deletion_status` and `steps_json`. A model is called only to extract typed facts or to answer yes/no on unmatched request text.",
        "",
        "Environment: `DELETION_AUDIT_MODEL` (default `grok-4.7`), `DELETION_AUDIT_FALLBACK_MODELS` (empty by default), `XAI_API_KEY`.",
        "",
    ]
    if agent is None or not agent.usages:
        lines.extend(
            [
                "No model call was made. Input tokens: 0. Output tokens: 0. Estimated cost: $0.",
                "",
                "Provider: xai. Model configured: DELETION_AUDIT_MODEL, default grok-4.7. Calls: 0.",
            ]
        )
    else:
        total_calls = total_in = total_out = 0
        total_cost = 0.0
        lines.append("| Model | Calls | Input tokens | Output tokens | Estimated USD |")
        lines.append("| --- | --- | --- | --- | --- |")
        for model, usage in sorted(agent.usages.items()):
            lines.append(
                f"| {usage.provider}/{model} | {usage.calls} | {usage.input_tokens} | {usage.output_tokens} | {usage.estimated_cost_usd:.4f} |"
            )
            total_calls += usage.calls
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            total_cost += usage.estimated_cost_usd
        requests = max(total_calls, 1)
        lines.extend(
            [
                "",
                f"Overall calls: {total_calls}",
                f"Overall input tokens: {total_in}",
                f"Overall output tokens: {total_out}",
                f"Average tokens per model call: {(total_in + total_out) / requests:.1f}",
                f"Estimated total cost: ${total_cost:.4f}",
                f"Estimated cost per model call: ${total_cost / requests:.4f}",
                "",
                "Cost uses a published-style estimate of $3 per million input tokens and $15 per million output tokens. It is not an invoice.",
            ]
        )
    if agent and agent.vision_skipped:
        lines.extend(["", f"Screenshots not sent to vision: {len(agent.vision_skipped)}."])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
