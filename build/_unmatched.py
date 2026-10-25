import csv
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "code"))
from classify import is_deletion_request

rows = list(csv.DictReader((root / "dataset" / "deletion_requests.csv").open(encoding="utf-8")))
unmatched = [row for row in rows if is_deletion_request(row["request_text"]) is None]
print("requests", len(rows))
print("unmatched", len(unmatched))
for row in unmatched[:30]:
    text = row["request_text"].replace("\n", " ")
    print(row["case_id"], text[:180])
