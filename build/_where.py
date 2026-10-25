"""Locate expected sample resource ids in participant evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
requests = list(csv.DictReader((DATASET / "sample_deletion_requests.csv").open(encoding="utf-8")))
expected = {row["case_id"]: row for row in csv.DictReader((DATASET / "sample_output.csv").open(encoding="utf-8"))}
manifest = list(csv.DictReader((DATASET / "evidence_files.csv").open(encoding="utf-8")))

wanted = set()
for row in expected.values():
    for step in json.loads(row["steps_json"]):
        wanted.add(step["resource_id"])

hits: dict[str, list[str]] = {item: [] for item in wanted}
for row in manifest:
    path = DATASET / row["file_path"]
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        continue
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    for resource_id in wanted:
        if resource_id in text:
            hits[resource_id].append(row["file_id"])

missing = sorted(resource_id for resource_id, files in hits.items() if not files)
print("expected resources", len(wanted))
print("missing from text evidence", len(missing))
for resource_id in missing:
    print(" ", resource_id)
print("--- sparse ---")
for resource_id, files in sorted(hits.items()):
    if 0 < len(files) <= 2:
        print(resource_id, files)
