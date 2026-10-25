"""Parse participant evidence into observations.

Manifest captured_at is the cutoff. A model may supply typed facts for
screenshots and textless pages. It does not choose a deletion status.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from constants import CATEGORIES, system_for

RESOURCE_RE = re.compile(
    r"\b(?:audit_record|data_flow|legal_hold|email_delivery|account|search|export|support|analytics|backup|tombstone|object|marketing|cache)_\d+\b"
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
USER_RE = re.compile(r"\buser_\d+\b", re.IGNORECASE)
HASH_RE = re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\+\d[\d \-]{6,}\d")
KV_RE = re.compile(r'([A-Za-z_]+)=(?:"([^"]*)"|(\S+))')
TRACE_RE = re.compile(r"\btr-[A-Za-z0-9]+\b")

KNOWN_SYSTEMS = {
    "account_service",
    "search_service",
    "security_service",
    "backup_service",
    "integration_service",
    "export_service",
    "identity_service",
    "support_platform",
    "analytics_platform",
    "marketing_platform",
    "object_storage",
    "email_delivery_service",
    "legal_service",
    "cache_service",
}
ALIASES = {"support_replica": "support_platform"}

COLLECTION_CATEGORY = {
    "profile_lookups": "USER_PROFILE",
    "customer_profiles": "USER_PROFILE",
    "customer_profiles_primary": "USER_PROFILE",
    "customer_profiles_failover_replica": "USER_PROFILE",
    "customer_profiles_replica": "USER_PROFILE",
    "customer_search_documents": "SEARCH_INDEX_ENTRY",
    "search_documents": "SEARCH_INDEX_ENTRY",
    "search_documents_primary": "SEARCH_INDEX_ENTRY",
    "index_queries": "SEARCH_INDEX_ENTRY",
    "customer_analytics_reports": "ANALYTICS_PROFILE",
    "customer_analytics_profiles": "ANALYTICS_PROFILE",
    "security_audit_events": "SECURITY_AUDIT_LOG",
    "security_audit_records": "SECURITY_AUDIT_LOG",
    "audit_records": "SECURITY_AUDIT_LOG",
    "deleted_customer_references": "ACCOUNT_TOMBSTONE",
    "connector_configurations": "DATA_FLOW",
    "connector_subscriptions": "DATA_FLOW",
    "connectors": "DATA_FLOW",
    "backup_catalog": "BACKUP_ARCHIVE",
    "backup_restore_entries": "BACKUP_ARCHIVE",
    "restore_entries": "BACKUP_ARCHIVE",
    "customer_export_jobs": "USER_EXPORT",
    "customer_exports": "USER_EXPORT",
    "exports": "USER_EXPORT",
    "support_records": "SUPPORT_MESSAGE",
    "tickets": "SUPPORT_MESSAGE",
    "retained_order_records": "LEGAL_HOLD_RECORD",
    "marketing_profiles": "MARKETING_PROFILE",
    "email_delivery_logs": "EMAIL_DELIVERY_LOG",
    "cache_entries": "CACHE_ENTRY",
}

COLLECTION_SYSTEM = {
    "profile_lookups": "account_service",
    "customer_profiles": "account_service",
    "customer_profiles_primary": "account_service",
    "customer_profiles_failover_replica": "account_service",
    "customer_profiles_replica": "account_service",
    "customer_search_documents": "search_service",
    "search_documents": "search_service",
    "search_documents_primary": "search_service",
    "index_queries": "search_service",
    "customer_analytics_reports": "analytics_platform",
    "customer_analytics_profiles": "analytics_platform",
    "security_audit_events": "security_service",
    "security_audit_records": "security_service",
    "audit_records": "security_service",
    "deleted_customer_references": "identity_service",
    "connector_configurations": "integration_service",
    "connector_subscriptions": "integration_service",
    "connectors": "integration_service",
    "backup_catalog": "backup_service",
    "backup_restore_entries": "backup_service",
    "restore_entries": "backup_service",
    "customer_export_jobs": "export_service",
    "customer_exports": "export_service",
    "exports": "export_service",
    "support_records": "support_platform",
    "tickets": "support_platform",
    "retained_order_records": "legal_service",
    "marketing_profiles": "marketing_platform",
    "email_delivery_logs": "email_delivery_service",
    "cache_entries": "cache_service",
}

EVENT_CATEGORY = (
    ("profile_lookup", "USER_PROFILE"),
    ("index_query", "SEARCH_INDEX_ENTRY"),
    ("audit_record", "SECURITY_AUDIT_LOG"),
    ("connector_", "DATA_FLOW"),
    ("analytics_profile", "ANALYTICS_PROFILE"),
    ("analytics_identity", "ANALYTICS_PROFILE"),
    ("contact_lookup", "SECONDARY_IDENTIFIER"),
    ("support_ticket", "SUPPORT_MESSAGE"),
    ("message_pii", "SUPPORT_MESSAGE"),
    ("message_scan", "SUPPORT_MESSAGE"),
    ("attachment_", "SUPPORT_ATTACHMENT"),
    ("restore_policy", "BACKUP_ARCHIVE"),
    ("restore_candidate", "BACKUP_ARCHIVE"),
    ("contact_query", "SUPPORT_ATTACHMENT"),
    ("deletion_marker", "SUPPORT_ATTACHMENT"),
)

EXPOSED_KEYS = {
    "email",
    "phone",
    "email_hash",
    "full_name",
    "display_name",
    "requester_email",
    "requester_name",
    "requester_phone",
    "owner_email",
    "owner_phone",
    "customer_email",
    "name",
    "matched_value",
}
LINK_KEYS = {
    "lookup_key",
    "match_key",
    "subject_key",
    "subject_ref",
    "subject_reference",
    "subject_selector",
    "customer_reference",
    "correlation_key",
    "scan_key",
    "user_id",
}


@dataclass
class Observation:
    file_id: str
    captured_at: str
    copy_key: str
    system_id: str
    resource_id: str
    category: str | None
    presence: str
    exposed: bool | None
    flow: str | None
    restore: str | None
    retention_until: str | None
    hold_active: bool | None
    tokens: set[str] = field(default_factory=set)
    cross_refs: set[str] = field(default_factory=set)
    encodes_user: bool = False


@dataclass
class ActivityLink:
    activity_id: str
    event_time: str
    resource_id: str
    system_id: str
    tokens: set[str]


def load_manifest(dataset: Path) -> list[dict[str, str]]:
    with (dataset / "evidence_files.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_index(dataset: Path, extractor=None) -> tuple[list[Observation], list[ActivityLink]]:
    observations: list[Observation] = []
    for row in load_manifest(dataset):
        path = dataset / row["file_path"]
        suffix = path.suffix.lower()
        if suffix == ".sql":
            observations.extend(_from_sql(row, path))
        elif suffix == ".json":
            observations.extend(_from_json(row, path))
        elif suffix in {".log", ".txt"}:
            observations.extend(_from_text(row, path))
        elif suffix == ".pdf":
            observations.extend(_from_pdf(row, path, extractor))
        elif suffix in {".png", ".jpg", ".jpeg"} and extractor is not None:
            observations.extend(extractor.extract_image(row, path))
    _mark_encoding(observations)
    return observations, _activity_links(dataset)


def _activity_links(dataset: Path) -> list[ActivityLink]:
    links: list[ActivityLink] = []
    with (dataset / "system_activity.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["source_system"] == "deletion_worker":
                continue
            tokens = _tokens(row["details"])
            if not tokens or not row["resource_id"]:
                continue
            if not (EMAIL_RE.search(row["details"]) or USER_RE.search(row["details"]) or HASH_RE.search(row["details"])):
                continue
            links.append(
                ActivityLink(
                    activity_id=row["activity_id"],
                    event_time=row["event_time"],
                    resource_id=row["resource_id"],
                    system_id=_normalize_system(row["target_system"]) or system_for(row["resource_id"]) or "",
                    tokens=tokens,
                )
            )
    return links


def _from_sql(row: dict[str, str], path: Path) -> list[Observation]:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(path.read_text(encoding="utf-8"))
    except sqlite3.DatabaseError:
        connection.close()
        return _from_text(row, path)
    found: list[Observation] = []
    tables = [name for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        if table == "snapshot_scope":
            continue
        columns = [info[1] for info in connection.execute(f'PRAGMA table_info("{table}")')]
        for values in connection.execute(f'SELECT * FROM "{table}"'):
            record = {column: values[index] for index, column in enumerate(columns)}
            nested = record.get("record_json")
            if isinstance(nested, str):
                try:
                    payload = json.loads(nested)
                except json.JSONDecodeError:
                    payload = None
                if isinstance(payload, dict):
                    record.update(payload)
                    document = payload.get("document")
                    if isinstance(document, dict):
                        record.update(document)
            collection = str(record.get("collection_name") or table)
            system = _normalize_system(str(record.get("origin_system") or "")) or COLLECTION_SYSTEM.get(collection) or COLLECTION_SYSTEM.get(table)
            category = COLLECTION_CATEGORY.get(collection) or COLLECTION_CATEGORY.get(table)
            observation = _from_record(row, table, record, system, category)
            if observation is not None:
                found.append(observation)
    connection.close()
    return found


def _from_json(row: dict[str, str], path: Path) -> list[Observation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    found: list[Observation] = []

    def walk(node: object, system: str | None, collection: str) -> None:
        if isinstance(node, dict):
            next_system = _normalize_system(str(node.get("data_store") or node.get("system_id") or "")) or system
            next_collection = str(node.get("collection") or collection)
            resource_id = str(node.get("resource_id") or "")
            if RESOURCE_RE.fullmatch(resource_id):
                flat = _flatten(node)
                category = _collection_category(next_collection, next_system) or _printed_category(flat)
                observation = _from_record(row, next_collection or path.stem, flat, next_system, category)
                if observation is not None:
                    found.append(observation)
            for key, value in node.items():
                child_system = next_system
                child_collection = next_collection
                if key in KNOWN_SYSTEMS or key in ALIASES or key.endswith("_service") or key.endswith("_platform"):
                    child_system = _normalize_system(key)
                if key in COLLECTION_CATEGORY or key == "profiles":
                    child_collection = key
                walk(value, child_system, child_collection)
        elif isinstance(node, list):
            for item in node:
                walk(item, system, collection)

    walk(payload, None, path.stem)
    return found


def _from_text(row: dict[str, str], path: Path) -> list[Observation]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if any(" | " in line and RESOURCE_RE.search(line) for line in lines):
        found = []
        for line_no, line in enumerate(lines, start=1):
            observation = _from_pipe(row, line, f"line:{line_no}")
            if observation is not None:
                found.append(observation)
        if found:
            return found
    groups: dict[str, list[tuple[int, dict[str, str], str]]] = {}
    for line_no, line in enumerate(lines, start=1):
        fields = _parse_fields(line)
        trace = fields.get("trace_id") or f"line:{line_no}"
        groups.setdefault(trace, []).append((line_no, fields, line))
    found = []
    for trace, group in groups.items():
        found.extend(_from_log_group(row, trace, group))
    return found


def _from_pdf(row: dict[str, str], path: Path, extractor) -> list[Observation]:
    text = _pdf_text(path)
    if _usable_text(text):
        return _from_document_text(row, path, text)
    if extractor is None:
        return []
    return extractor.extract_pdf(row, path)


def _from_document_text(row: dict[str, str], path: Path, text: str) -> list[Observation]:
    matches = list(RESOURCE_RE.finditer(text))
    found: list[Observation] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        window = text[max(0, match.start() - 500) : end]
        resource_id = match.group(0)
        category = _printed_category_text(window) or _printed_category_text(text)
        if category is None and resource_id.startswith("support_") and "attachment" in path.name.lower():
            category = "SUPPORT_ATTACHMENT"
        if category is None and resource_id.startswith("audit_record_") and "retain until" in text.lower():
            category = "SECURITY_AUDIT_LOG"
        system = system_for(resource_id) or ""
        record = {"resource_id": resource_id, "line": window}
        observation = _from_record(row, f"pdf:{resource_id}", record, system, category, extra_text=window)
        if observation is not None:
            observation.presence = "present"
            observation.exposed = bool(_direct_identifiers(window))
            found.append(observation)
    return found


def _from_pipe(row: dict[str, str], line: str, copy_key: str) -> Observation | None:
    if " | " not in line or not RESOURCE_RE.search(line):
        return None
    parts = [part.strip() for part in line.split("|")]
    resource_id = next((part for part in parts if RESOURCE_RE.fullmatch(part)), "")
    if not resource_id:
        return None
    system = next((part for part in parts if _normalize_system(part)), None)
    category = next((part for part in parts if part in CATEGORIES), None)
    state = next((part for part in parts if part in {"NOT_FOUND", "FOUND", "IDENTIFIABLE", "ANONYMIZED", "REDACTED", "ACTIVE", "DISABLED", "BLOCKED"}), None)
    tail = parts[-1] if parts else ""
    record = {
        "resource_id": resource_id,
        "system_id": system,
        "category": category,
        "state": state,
        "line": line,
        "tail": tail,
    }
    return _from_record(row, copy_key, record, system, category, extra_text=line)


def _from_log_group(row: dict[str, str], copy_key: str, group: list[tuple[int, dict[str, str], str]]) -> list[Observation]:
    fields: dict[str, str] = {}
    events: list[str] = []
    text = "\n".join(line for _, _, line in group)
    for _, item, _ in group:
        event = item.get("event")
        if event:
            events.append(event)
        for key, value in item.items():
            if value and value.lower() not in {"null", "none"}:
                fields[key] = value
    resource_id = fields.get("resource_id", "")
    if not RESOURCE_RE.fullmatch(resource_id):
        found = RESOURCE_RE.findall(text)
        resource_id = found[0] if found else ""
    if not resource_id:
        return []
    if _log_presence(fields, events) is None and "enabled" not in fields and "restore_allowed" not in fields:
        return []
    system = _normalize_system(fields.get("service", "")) or system_for(resource_id)
    category = _event_category(" ".join(events)) or _printed_category_text(text)
    record = dict(fields)
    record["resource_id"] = resource_id
    observation = _from_record(row, copy_key, record, system, category, extra_text=text)
    if observation is None:
        return []
    observation.presence = _log_presence(fields, events) or observation.presence
    observation.exposed = False if observation.presence == "absent" else _exposed_fields(fields)
    if observation.presence == "present" and observation.exposed is None:
        observation.exposed = bool(_direct_identifiers(text) - _query_tokens(fields))
    observation.flow = _flow_from_fields(fields, text)
    observation.restore = _restore_from_fields(fields, text)
    observation.tokens = _tokens(text)
    observation.tokens.update(_query_tokens(fields))
    observation.cross_refs = set(RESOURCE_RE.findall(text)) - {resource_id}
    if fields.get("retention_until"):
        observation.retention_until = fields["retention_until"]
    return [observation]


def _from_record(
    row: dict[str, str],
    copy_key: str,
    record: dict,
    system: str | None,
    category: str | None,
    extra_text: str = "",
) -> Observation | None:
    resource_id = str(record.get("resource_id") or "")
    if not RESOURCE_RE.fullmatch(resource_id):
        return None
    system_id = _normalize_system(system or "") or _normalize_system(str(record.get("system_id") or record.get("origin_system") or record.get("service") or "")) or system_for(resource_id) or ""
    if not system_id:
        return None
    text = extra_text + " " + " ".join(str(value) for value in record.values() if value is not None)
    if category is None:
        category = _printed_category(record) or _collection_category(copy_key, system_id) or _category_from_text(text)
    presence, exposed, flow, restore = _state_from_record(record, text)
    tokens = _tokens(text)
    for key in LINK_KEYS:
        value = record.get(key)
        if value:
            tokens.update(_tokens(str(value)))
    cross_refs = set(RESOURCE_RE.findall(text)) - {resource_id}
    for key in ("source_resource_id", "customer_reference", "subject_reference", "lookup_key"):
        value = record.get(key)
        if value and RESOURCE_RE.fullmatch(str(value)):
            cross_refs.add(str(value))
    retention = record.get("retention_until") or record.get("retained_until")
    hold = record.get("hold_active")
    if hold is None and category == "LEGAL_HOLD_RECORD":
        hold = record.get("active")
    return Observation(
        file_id=row["file_id"],
        captured_at=row["captured_at"],
        copy_key=copy_key,
        system_id=system_id,
        resource_id=resource_id,
        category=category,
        presence=presence,
        exposed=exposed,
        flow=flow,
        restore=restore,
        retention_until=str(retention) if retention else None,
        hold_active=None if hold is None else str(hold).lower() in {"1", "true", "active", "yes"},
        tokens=tokens,
        cross_refs=cross_refs,
    )


def _flatten(record: dict) -> dict:
    flat = dict(record)
    for key in ("profile", "document"):
        value = record.get(key)
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                flat.setdefault(child_key, child_value)
    hits = record.get("hits")
    if isinstance(hits, dict):
        documents = hits.get("documents")
        if isinstance(documents, list):
            for document in documents:
                if isinstance(document, dict):
                    for child_key, child_value in document.items():
                        flat.setdefault(child_key, child_value)
    return flat


def _state_from_record(record: dict, text: str) -> tuple[str, bool | None, str | None, str | None]:
    status = record.get("status_code", record.get("http_status"))
    state = str(record.get("state") or record.get("account_status") or "").upper()
    if str(status) == "404" or state in {"NOT_FOUND", "ABSENT"} or "ROWS=0" in text.upper() or "HTTP_STATUS=404" in text.upper():
        presence = "absent"
    elif str(status) == "200" or state in {"FOUND", "PRESENT", "IDENTIFIABLE", "ANONYMIZED", "REDACTED", "ACTIVE", "DELETION_PENDING"}:
        presence = "present"
    elif record.get("profile") is None and "profile" in record and str(status) == "404":
        presence = "absent"
    elif _record_has_body(record):
        presence = "present"
    else:
        presence = "unknown"
    exposed = False if presence == "absent" else _exposed_fields(record)
    if presence == "present" and exposed is False and state == "IDENTIFIABLE":
        exposed = True
    if state in {"ANONYMIZED", "REDACTED"}:
        exposed = False
        presence = "present"
    flow = _flow_from_fields(record, text)
    restore = _restore_from_fields(record, text)
    if state == "DISABLED":
        flow = "disabled"
    if state == "BLOCKED":
        restore = "blocked"
    if state == "ACTIVE" and (record.get("category") == "DATA_FLOW" or "data_flow" in text):
        flow = flow or "active"
    if state == "ACTIVE" and (record.get("category") == "BACKUP_ARCHIVE" or "backup_" in text):
        restore = restore or "open"
    return presence, exposed, flow, restore


def _record_has_body(record: dict) -> bool:
    ignored = {"resource_id", "observed_at", "updated_at", "created_at", "system_id", "origin_system", "collection_name", "index_name"}
    for key, value in record.items():
        if key in ignored or value is None or value == "":
            continue
        if key == "profile" and value is None:
            continue
        return True
    return False


def _exposed_fields(record: dict) -> bool:
    for key in EXPOSED_KEYS:
        value = record.get(key)
        if value is None or str(value).lower() in {"", "null", "none"}:
            continue
        text = str(value)
        if EMAIL_RE.search(text) or PHONE_RE.search(text) or HASH_RE.search(text) or key in {"full_name", "display_name", "requester_name", "name"}:
            return True
    return False


def _flow_from_fields(fields: dict, text: str) -> str | None:
    if "enabled" in fields and fields.get("enabled") is not None and str(fields.get("enabled")).lower() not in {"", "null", "none"}:
        return "active" if str(fields.get("enabled")).lower() in {"1", "true"} else "disabled"
    lowered = text.lower()
    if "enabled=true" in lowered or "enabled=1" in lowered:
        return "active"
    if "enabled=false" in lowered or "enabled=0" in lowered:
        return "disabled"
    return None


def _restore_from_fields(fields: dict, text: str) -> str | None:
    if "restore_allowed" in fields and fields.get("restore_allowed") is not None and str(fields.get("restore_allowed")).lower() not in {"", "null", "none"}:
        return "blocked" if str(fields.get("restore_allowed")).lower() in {"0", "false"} else "open"
    lowered = text.lower()
    if "restore_allowed=false" in lowered or "restore_allowed=0" in lowered:
        return "blocked"
    if "restore_allowed=true" in lowered or "restore_allowed=1" in lowered:
        return "open"
    if str(fields.get("deletion_block") or "").lower() == "false" or str(fields.get("eligible") or "").lower() == "true":
        return "open"
    if str(fields.get("deletion_block") or "").lower() == "true":
        return "blocked"
    return None


def _log_presence(fields: dict[str, str], events: list[str]) -> str | None:
    event_text = " ".join(events)
    completed = any(
        "completed" in event or event in {"connector_heartbeat", "deletion_marker_check", "restore_candidate_evaluated"} or "pii_scan" in event
        for event in events
    )
    has_state = completed or any(key in fields for key in ("rows", "http_status", "status_code", "enabled", "restore_allowed", "marker_found"))
    if not has_state:
        return None
    if fields.get("rows") == "0" or fields.get("http_status") == "404" or fields.get("status_code") == "404":
        return "absent"
    if fields.get("result") == "hit" or (fields.get("rows") not in {None, ""} and fields.get("rows") != "0"):
        return "present"
    if fields.get("http_status") == "200" or fields.get("status_code") == "200":
        return "present"
    if fields.get("marker_found") == "false":
        return "present"
    if "enabled" in fields or "restore_allowed" in fields or "eligible" in fields or "heartbeat" in event_text or "pii_scan" in event_text or "scan" in event_text:
        return "present"
    if completed and any(fields.get(key) not in {None, "", "null"} for key in ("email", "requester_email", "requester_name", "customer_email", "audience_cohort", "customer_reference", "subject_reference", "retention_until", "event_code")):
        return "present"
    if completed:
        return "unknown"
    return None


def _query_tokens(fields: dict) -> set[str]:
    found: set[str] = set()
    for key in LINK_KEYS:
        value = fields.get(key)
        if value:
            found.update(_tokens(str(value)))
    return found


def _direct_identifiers(text: str) -> set[str]:
    return _tokens(text)


def _parse_fields(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    start = line.find("{")
    if start != -1:
        try:
            payload = json.loads(line[start:])
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for key, value in payload.items():
                if value is not None:
                    fields[key] = str(value)
    for key, quoted, bare in KV_RE.findall(line):
        fields[key] = quoted if quoted != "" else bare
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_]+", line):
        if token in KNOWN_SYSTEMS or token in ALIASES:
            fields.setdefault("service", token)
    trace = fields.get("trace_id") or ""
    if not trace:
        match = TRACE_RE.search(line)
        if match:
            fields["trace_id"] = match.group(0)
    return fields


def _collection_category(collection: str, system: str | None) -> str | None:
    if collection == "profiles":
        if system == "analytics_platform":
            return "ANALYTICS_PROFILE"
        if system == "account_service":
            return "USER_PROFILE"
    return COLLECTION_CATEGORY.get(collection)


def _event_category(events: str) -> str | None:
    for needle, category in EVENT_CATEGORY:
        if needle in events:
            return category
    return None


def _printed_category(record: dict) -> str | None:
    for value in record.values():
        if isinstance(value, str) and value in CATEGORIES:
            return value
    return None


def _printed_category_text(text: str) -> str | None:
    for category in CATEGORIES:
        if category in text:
            return category
    return None


def _category_from_text(text: str) -> str | None:
    lowered = text.lower()
    for needle, category in (
        ("profile_lookup", "USER_PROFILE"),
        ("audit_record_read", "SECURITY_AUDIT_LOG"),
        ("analytics_profile", "ANALYTICS_PROFILE"),
        ("connector_config", "DATA_FLOW"),
        ("restore_policy", "BACKUP_ARCHIVE"),
        ("index_query", "SEARCH_INDEX_ENTRY"),
        ("support_ticket", "SUPPORT_MESSAGE"),
        ("attachment catalog", "SUPPORT_ATTACHMENT"),
    ):
        if needle in lowered:
            return category
    return None


def _normalize_system(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value in ALIASES:
        return ALIASES[value]
    if value in KNOWN_SYSTEMS:
        return value
    return None


def _tokens(text: str) -> set[str]:
    found = {match.lower() for match in EMAIL_RE.findall(text)}
    found.update(match.lower() for match in USER_RE.findall(text))
    found.update(match.lower() for match in HASH_RE.findall(text))
    for phone in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 8:
            found.add(digits)
    return found


def _pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _usable_text(text: str) -> bool:
    return bool(RESOURCE_RE.search(text) or EMAIL_RE.search(text) or USER_RE.search(text))


def _mark_encoding(observations: list[Observation]) -> None:
    grouped: dict[tuple[str, str], list[Observation]] = {}
    for observation in observations:
        if observation.resource_id.startswith("account_") and observation.presence == "present":
            grouped.setdefault((observation.file_id, observation.copy_key), []).append(observation)
    for group in grouped.values():
        paired = []
        for observation in group:
            users = [token for token in observation.tokens if token.startswith("user_")]
            if len(users) == 1:
                paired.append((observation, users[0]))
        if not paired:
            continue
        if all(_same_number(observation.resource_id, user_id) for observation, user_id in paired):
            for observation, _user_id in paired:
                observation.encodes_user = True


def _same_number(resource_id: str, user_id: str) -> bool:
    return resource_id.split("_")[-1].lstrip("0") == user_id.split("_")[-1].lstrip("0")
