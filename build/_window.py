import csv, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
reqs = list(csv.DictReader((root/"dataset"/"sample_deletion_requests.csv").open(encoding="utf-8")))
gold = {r["case_id"]: r for r in csv.DictReader((root/"dataset"/"sample_output.csv").open(encoding="utf-8"))}
acts = list(csv.DictReader((root/"dataset"/"system_activity.csv").open(encoding="utf-8")))
for req in reqs:
    steps = json.loads(gold[req["case_id"]]["steps_json"])
    accounts = sorted({s["resource_id"] for s in steps if s["resource_id"].startswith("account_")})
    audits = sorted({s["resource_id"] for s in steps if s["resource_id"].startswith("audit_record_")})
    start, end = req["requested_at"], req["reported_at"]
    window = [
        a for a in acts
        if start <= a["event_time"] <= end and a["source_system"] == "deletion_worker"
    ]
    acc = [a["resource_id"] for a in window if a["resource_id"].startswith("account_")]
    aud = [a["resource_id"] for a in window if a["resource_id"].startswith("audit_record_")]
    print(req["case_id"], "want", accounts, audits)
    print("  window accounts", acc)
    print("  window audits", aud[:8], "n", len(aud))
