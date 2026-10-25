import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/"code"))
from evidence_index import build_index
obs, links = build_index(root/"dataset")
for resource in ["support_5569", "account_6523", "backup_3245", "audit_record_4902", "account_3960"]:
    print("==", resource)
    for item in obs:
        if item.resource_id == resource:
            print(item.file_id, item.presence, item.category, item.exposed, item.flow, item.restore, sorted(item.tokens)[:8], item.copy_key)
