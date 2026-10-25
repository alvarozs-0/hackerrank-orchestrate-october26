import csv, json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/"code"))
from identity import load_identities
from evidence_index import build_index
from decide import decide_case
from classify import is_deletion_request

dataset = root/"dataset"
requests = list(csv.DictReader((dataset/"sample_deletion_requests.csv").open(encoding="utf-8")))
expected = {r["case_id"]: r for r in csv.DictReader((dataset/"sample_output.csv").open(encoding="utf-8"))}
identities = load_identities(dataset)
obs, links = build_index(dataset)
print("obs", len(obs))
for req in requests:
    if not is_deletion_request(req["request_text"]):
        continue
    subject = identities.resolve(req["email"])
    outcome = decide_case(req["audit_at"], subject, obs, links)
    got = [s["resource_id"] for s in outcome.steps if s["resource_id"].startswith("account_") and s["phase"]=="VERIFICATION"]
    gold = [s["resource_id"] for s in json.loads(expected[req["case_id"]]["steps_json"]) if s["resource_id"].startswith("account_")]
    if got != gold:
        print(req["case_id"], "got", got, "want", gold)
