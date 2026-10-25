import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
payload = json.loads((root/"dataset/evidence/records/service_resource_export_20260915_114455.json").read_text(encoding="utf-8"))
exports = payload["service_exports"]
print("ACCOUNTS")
for item in exports["account_service"]["profile_lookups"]:
    profile = item.get("profile") or {}
    print(item["resource_id"], item.get("status_code"), profile.get("email"), profile.get("customer_reference"), item.get("observed_at"))
print("AUDITS")
for item in exports["security_service"]["audit_records"]:
    print(item["resource_id"], item.get("subject_reference"), item.get("observed_at"), item.get("event_code"))
print("ANALYTICS")
for item in exports["analytics_platform"]["profiles"]:
    print(item["resource_id"], item.get("email"), item.get("customer_reference"), item.get("audience_cohort"), item.get("observed_at"))
