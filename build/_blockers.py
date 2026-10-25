import csv
import sys
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "code"))
from main import _evaluate, _read_csv, DATASET

requests = _read_csv(DATASET / "deletion_requests.csv")
results, blockers = _evaluate(requests, require_vision=False)
print("decided", len(results), "blocked", len(blockers))
reasons = Counter(reason.split(":")[0] for reasons in blockers.values() for reason in reasons[:1])
print(reasons)
for case_id, reasons in list(blockers.items())[:8]:
    print(case_id, reasons[0])
