import sys
from collections import Counter, defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "code"))
from evidence_index import build_index
from identity import load_identities
from main import DATASET, _read_csv
from decide import decide_case
from classify import is_deletion_request

requests = _read_csv(DATASET / "deletion_requests.csv")
identities = load_identities(DATASET)
observations, links = build_index(DATASET)
by_resource = defaultdict(list)
for item in observations:
    by_resource[item.resource_id].append(item)

missing = Counter()
unmatched = Counter()
for request in requests:
    decision = is_deletion_request(request["request_text"])
    if not decision:
        continue
    subject = identities.resolve(request["email"])
    if subject is None:
        continue
    outcome = decide_case(request["audit_at"], subject, observations, links)
    if not outcome.blockers:
        continue
    reason = outcome.blockers[0]
    if reason.startswith("no printed category"):
        ids = reason.split(": ", 1)[1].split(", ")
        for resource_id in ids:
            items = [item for item in by_resource.get(resource_id, []) if item.captured_at <= request["audit_at"]]
            keys = Counter((item.copy_key, item.system_id, item.presence, item.flow, item.restore) for item in items)
            missing[resource_id.split("_")[0] + " " + str(keys.most_common(1))] += 1
    elif reason.startswith("unmatched rule"):
        unmatched[reason] += 1

print("MISSING PREFIXES")
for key, count in missing.most_common(30):
    print(count, key)
print("UNMATCHED")
for key, count in unmatched.most_common(20):
    print(count, key)
