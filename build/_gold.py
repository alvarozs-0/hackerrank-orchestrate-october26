import csv, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
rows = list(csv.DictReader((root/"dataset"/"sample_output.csv").open(encoding="utf-8")))
for row in rows:
    if row["case_id"] not in {"case_01","case_05","case_06","case_08","case_12","case_15","case_02"}:
        continue
    steps = json.loads(row["steps_json"])
    print(row["case_id"], row["deletion_status"])
    for step in steps:
        print(f"  {step['phase'][:3]} {step['operation']} {step['resource_id']} {step['evidence_id']}")
