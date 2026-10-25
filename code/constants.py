"""Contract enums and the prefix-to-system map observed in the samples."""

from __future__ import annotations

FINDING_ORDER = (
    "REPORT_REMAINING_RECORD",
    "REPORT_EXPOSED_PII",
    "REPORT_ACTIVE_DATA_FLOW",
    "REPORT_RESTORE_RISK",
)

REMEDIATION_ORDER = (
    "DISABLE_DATA_FLOW",
    "BLOCK_RESTORE",
    "DELETE_RECORD",
    "REDACT_RECORD",
    "ANONYMIZE_RECORD",
)

VERIFICATION_ORDER = (
    "VERIFY_RECORD_ABSENT",
    "VERIFY_RECORD_PRESENT",
    "VERIFY_RECORD_REDACTED",
    "VERIFY_RECORD_ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED",
    "VERIFY_RESTORE_BLOCKED",
)

OPERATION_STATE = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
PHASE_OPERATIONS = {
    "FINDING": FINDING_ORDER,
    "REMEDIATION": REMEDIATION_ORDER,
    "VERIFICATION": VERIFICATION_ORDER,
}

PREFIX_SYSTEM = (
    ("audit_record_", "security_service"),
    ("data_flow_", "integration_service"),
    ("legal_hold_", "legal_service"),
    ("email_delivery_", "email_delivery_service"),
    ("account_", "account_service"),
    ("search_", "search_service"),
    ("export_", "export_service"),
    ("support_", "support_platform"),
    ("analytics_", "analytics_platform"),
    ("backup_", "backup_service"),
    ("tombstone_", "identity_service"),
    ("object_", "object_storage"),
    ("marketing_", "marketing_platform"),
    ("cache_", "cache_service"),
)

CATEGORIES = {
    "USER_PROFILE",
    "SECONDARY_IDENTIFIER",
    "SEARCH_INDEX_ENTRY",
    "CACHE_ENTRY",
    "SUPPORT_MESSAGE",
    "SUPPORT_ATTACHMENT",
    "ANALYTICS_PROFILE",
    "PRODUCT_TELEMETRY",
    "USER_EXPORT",
    "MARKETING_PROFILE",
    "EMAIL_DELIVERY_LOG",
    "SECURITY_AUDIT_LOG",
    "LEGAL_HOLD_RECORD",
    "BACKUP_ARCHIVE",
    "ACCOUNT_TOMBSTONE",
    "DATA_FLOW",
}

DELETE_CATEGORIES = {
    "USER_PROFILE",
    "SECONDARY_IDENTIFIER",
    "SEARCH_INDEX_ENTRY",
    "CACHE_ENTRY",
    "SUPPORT_ATTACHMENT",
    "USER_EXPORT",
    "MARKETING_PROFILE",
}

REDACT_CATEGORIES = {"SUPPORT_MESSAGE", "EMAIL_DELIVERY_LOG", "ACCOUNT_TOMBSTONE"}
ANONYMIZE_CATEGORIES = {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"}
RETAIN_CATEGORIES = {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE"}

TABLE_CATEGORY = {
    "customer_profiles": "USER_PROFILE",
    "customer_profiles_primary": "USER_PROFILE",
    "customer_profiles_failover_replica": "USER_PROFILE",
    "profile_lookups": "USER_PROFILE",
    "customer_profiles_replica": "USER_PROFILE",
    "search_documents": "SEARCH_INDEX_ENTRY",
    "search_documents_primary": "SEARCH_INDEX_ENTRY",
    "security_audit_records": "SECURITY_AUDIT_LOG",
    "security_audit_events": "SECURITY_AUDIT_LOG",
    "deleted_customer_references": "ACCOUNT_TOMBSTONE",
    "customer_analytics_reports": "ANALYTICS_PROFILE",
    "profiles": "ANALYTICS_PROFILE",
}


def system_for(resource_id: str) -> str | None:
    for prefix, system_id in PREFIX_SYSTEM:
        if resource_id.startswith(prefix):
            return system_id
    return None
