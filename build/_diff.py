import csv, json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "code"))
from main import _evaluate, _read_csv, DATASET

requests = _read_csv(DATASET / "sample_deletion_requests.csv")
expected = {row["case_id"]: row for row in _read_csv(DATASET / "sample_output.csv")}
results, blockers = _evaluate(requests, require_vision=False)
got = {row["case_id"]: row for row in results}

def tuples(payload):
    return [(s["phase"], s["operation"], s["state"], s["system_id"], s["resource_id"], s["evidence_id"]) for s in json.loads(payload)]

print("blocked", blockers)
for case_id, gold in expected.items():
    if case_id not in got:
        print("MISSING", case_id)
        continue
    row = got[case_id]
    gt, ot = tuples(gold["steps_json"]), tuples(row["steps_json"])
    if row["deletion_status"] == gold["deletion_status"] and gt == ot:
        continue
    print("=" * 60)
    print(case_id, "got", row["deletion_status"], "want", gold["deletion_status"])
    gs, os_ = set(gt), set(ot)
    for item in sorted(gs - os_):
        print("  missing", item)
    for item in sorted(os_ - gs):
        print("  extra  ", item)
