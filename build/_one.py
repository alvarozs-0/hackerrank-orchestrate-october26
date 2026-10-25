import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "code"))
from evidence_index import build_index
obs, _ = build_index(root / "dataset")
for item in obs:
    if item.resource_id == "backup_3250":
        print(item.file_id, item.category, item.presence, item.restore, item.flow, item.copy_key, item.captured_at)
