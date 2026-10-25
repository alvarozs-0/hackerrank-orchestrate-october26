import csv
import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
fields = ["phase", "operation", "state", "system_id", "resource_id", "evidence_id"]
expected = {r["case_id"]: r for r in csv.DictReader((root / "dataset" / "sample_output.csv").open(encoding="utf-8"))}
got = {r["case_id"]: r for r in csv.DictReader((root / "build" / "sample_predictions.csv").open(encoding="utf-8"))}
status = sequence = 0
field_hits = field_total = 0
for case_id, gold in expected.items():
    row = got.get(case_id)
    if row is None:
        print("missing", case_id)
        continue
    status += row["deletion_status"] == gold["deletion_status"]
    gs = json.loads(gold["steps_json"])
    os_ = json.loads(row["steps_json"])
    sequence += [tuple(s[f] for f in fields) for s in gs] == [tuple(s[f] for f in fields) for s in os_]
    for g, o in zip(gs, os_):
        for name in fields:
            field_total += 1
            field_hits += g[name] == o[name]
    field_total += abs(len(gs) - len(os_)) * len(fields)
print(f"sample_status {status}/{len(expected)}")
print(f"sample_sequence {sequence}/{len(expected)}")
print(f"sample_fields {field_hits}/{field_total}")

rows = list(csv.DictReader((root / "output.csv").open(encoding="utf-8")))
print("output_rows", len(rows))
print("statuses", Counter(r["deletion_status"] for r in rows))
print("empty", sum(1 for r in rows if r["steps_json"] == "[]"))
bad = 0
for row in rows:
    steps = json.loads(row["steps_json"])
    if not isinstance(steps, list):
        bad += 1
        continue
    for index, step in enumerate(steps, start=1):
        if step.get("step_no") != index or set(step) != {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}:
            bad += 1
            break
print("invalid_rows", bad)
ids = [row["case_id"] for row in rows]
print("sorted", ids == sorted(ids, key=lambda item: int(item.split("_")[1])))
