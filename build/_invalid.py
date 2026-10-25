import csv, json
from collections import Counter
from pathlib import Path
rows = list(csv.DictReader(Path("output.csv").open(encoding="utf-8")))
reasons = Counter()
examples = []
for row in rows:
    steps = json.loads(row["steps_json"])
    for index, step in enumerate(steps, start=1):
        keys = set(step)
        expected = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
        if step.get("step_no") != index:
            reasons["step_no"] += 1
            if len(examples) < 3:
                examples.append((row["case_id"], index, step.get("step_no"), list(keys)))
            break
        if keys != expected:
            reasons["keys:" + ",".join(sorted(keys - expected))] += 1
            if len(examples) < 3:
                examples.append((row["case_id"], index, step, sorted(keys - expected)))
            break
print(reasons)
print(examples)
