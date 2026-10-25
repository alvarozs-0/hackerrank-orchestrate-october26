import csv, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
expected = {r["case_id"]: r for r in csv.DictReader((root/"dataset/sample_output.csv").open(encoding="utf-8"))}
got = {r["case_id"]: r for r in csv.DictReader((root/"build/sample_predictions.csv").open(encoding="utf-8"))}
fields = ["phase", "operation", "state", "system_id", "resource_id", "evidence_id"]
status = step = 0
field_hits = field_total = 0
for case_id, gold in expected.items():
    row = got[case_id]
    status += row["deletion_status"] == gold["deletion_status"]
    gs = json.loads(gold["steps_json"])
    os_ = json.loads(row["steps_json"])
    step += [tuple(s[f] for f in fields) for s in gs] == [tuple(s[f] for f in fields) for s in os_]
    for g, o in zip(gs, os_):
        for f in fields:
            field_total += 1
            field_hits += g[f] == o[f]
    field_total += abs(len(gs) - len(os_)) * len(fields)
print("status", status, len(expected))
print("sequence", step, len(expected))
print("fields", field_hits, field_total, field_hits / field_total if field_total else 0)
