"""Compare sample predictions to gold and dump observation gaps."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from decide import decide_case
from evidence_index import build_index
from identity import load_identities
from classify import is_deletion_request

DATASET = ROOT / "dataset"
requests = list(csv.DictReader((DATASET / "sample_deletion_requests.csv").open(encoding="utf-8")))
expected = {row["case_id"]: row for row in csv.DictReader((DATASET / "sample_output.csv").open(encoding="utf-8"))}
identities = load_identities(DATASET)
observations, links = build_index(DATASET)

print(f"observations={len(observations)} links={len(links)}")
by_resource = defaultdict(list)
for item in observations:
    by_resource[item.resource_id].append(item)

def tuples(payload):
    steps = json.loads(payload)
    return [
        (step["phase"], step["operation"], step["state"], step["system_id"], step["resource_id"], step["evidence_id"])
        for step in steps
    ]

for request in requests:
    case_id = request["case_id"]
    gold = expected[case_id]
    decision = is_deletion_request(request["request_text"])
    subject = identities.resolve(request["email"]) if decision else None
    outcome = None
    if decision and subject:
        outcome = decide_case(request["audit_at"], subject, observations, links)
    gold_steps = tuples(gold["steps_json"])
    got_status = outcome.status if outcome else ("NOT_APPLICABLE" if decision is False else "BLOCKED")
    got_steps = tuples(json.dumps(outcome.steps)) if outcome and outcome.status else []
    if got_status == gold["deletion_status"] and got_steps == gold_steps:
        continue
    print("=" * 80)
    print(case_id, "expected", gold["deletion_status"], "got", got_status)
    if outcome and outcome.blockers:
        print(" blockers", outcome.blockers)
    print(" email", request["email"], "audit", request["audit_at"], "subject", subject.user_id if subject else None)
    print(" text", request["request_text"][:180].replace("\n", " "))
    gold_ids = {step[4] for step in gold_steps}
    print(" expected resources:")
    for resource_id in sorted(gold_ids):
        items = [item for item in by_resource.get(resource_id, []) if item.captured_at <= request["audit_at"]]
        cats = sorted({item.category or "-" for item in items})
        files = sorted({item.file_id for item in items})
        pres = sorted({item.presence for item in items})
        flows = sorted({str(item.flow) for item in items})
        print(f"  {resource_id}: obs={len(items)} cats={cats} presence={pres} flow={flows} files={files[:8]}")
    if got_steps != gold_steps and got_status == gold["deletion_status"]:
        print(" step diff")
        gs, os_ = set(gold_steps), set(got_steps)
        for missing in sorted(gs - os_):
            print("  missing", missing)
        for extra in sorted(os_ - gs):
            print("  extra  ", extra)
