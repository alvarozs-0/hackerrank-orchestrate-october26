"""Parse participant evidence into observations. Manifest captured_at is the cutoff."""

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
USER_RE = re.compile(r"\buser_\d+\b")
HASH_RE = re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\+\d[\d \-]{6,}\d")

ABSENT_TOKENS = {"NOT_FOUND", "ABSENT", "404"}
PRESENT_TOKENS = {"FOUND", "PRESENT", "IDENTIFIABLE", "ACTIVE", "200"}
ANON_TOKENS = {"ANONYMIZED"}
REDACT_TOKENS = {"REDACTED"}


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


def build_index(dataset: Path) -> tuple[list[Observation], list[ActivityLink]]:
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
            observations.extend(_from_pdf(row, path))
    return observations, _activity_links(dataset)


def _activity_links(dataset: Path) -> list[ActivityLink]:
    links: list[ActivityLink] = []
    with (dataset / "system_activity.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
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
                    system_id=row["target_system"] or system_for(row["resource_id"]) or "",
                    tokens=tokens,
                )
            )
    return links


def _from_sql(row: dict[str, str], path: Path) -> list[Observation]:
    sql = path.read_text(encoding="utf-8")
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(sql)
    except sqlite3.DatabaseError:
        connection.close()
        return _from_text(row, path)
    found: list[Observation] = []
    tables = [name for (name,) in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        columns = [info[1] for info in connection.execute(f'PRAGMA table_info("{table}")')]
        for values in connection.execute(f'SELECT * FROM "{table}"'):
            record = {column: values[index] for index, column in enumerate(columns)}
            observation = _from_mapping(row, table, record, table)
            if observation is not None:
                found.append(observation)
    connection.close()
    _mark_encoding(found)
    return found


def _from_json(row: dict[str, str], path: Path) -> list[Observation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    found: list[Observation] = []

    def walk(node: object, copy_key: str) -> None:
        if isinstance(node, dict):
            next_key = str(node.get("collection") or node.get("data_store") or copy_key)
            if "resource_id" in node:
                observation = _from_mapping(row, next_key, node, next_key)
                if observation is not None:
                    found.append(observation)
            for key, value in node.items():
                if key.endswith("_service") or key.endswith("_platform"):
                    child_key = key
                else:
                    child_key = str(node.get("collection") or node.get("data_store") or copy_key)
                walk(value, child_key)
        elif isinstance(node, list):
            for item in node:
                walk(item, copy_key)

    walk(payload, path.stem)
    _mark_encoding(found)
    return found


def _from_text(row: dict[str, str], path: Path) -> list[Observation]:
    found: list[Observation] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if "resource_id=" in line or "|" in line:
            observation = _from_line(row, line, f"line:{line_no}")
            if observation is not None:
                found.append(observation)
    return found


def _from_pdf(row: dict[str, str], path: Path) -> list[Observation]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    fake = row.copy()
    observations: list[Observation] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        observation = _from_line(fake, line, f"pdf:{line_no}")
        if observation is not None:
            observations.append(observation)
    return observations


def _from_line(row: dict[str, str], line: str, copy_key: str) -> Observation | None:
    resources = RESOURCE_RE.findall(line)
    if not resources:
        return None
    resource_id = resources[0]
    parts = [part.strip() for part in line.split("|")]
    system_id = next((part for part in parts if part.endswith("_service") or part.endswith("_platform")), None)
    category = next((part for part in parts if part in CATEGORIES), None)
    state_token = next((part for part in parts if part in ABSENT_TOKENS | PRESENT_TOKENS | ANON_TOKENS | REDACT_TOKENS | {"DISABLED", "BLOCKED", "ACTIVE"}), None)
    fields = _key_values(line)
    mapping = {
        "resource_id": resource_id,
        "system_id": system_id or fields.get("service"),
        "category": category,
        "state": state_token,
        **fields,
    }
    mapping["line"] = line
    return _from_mapping(row, copy_key, mapping, copy_key)


def _from_mapping(row: dict[str, str], copy_key: str, record: dict, category_hint: str) -> Observation | None:
    resource_id = str(record.get("resource_id") or "")
    if not RESOURCE_RE.fullmatch(resource_id):
        nested = RESOURCE_RE.findall(" ".join(str(value) for value in record.values() if value is not None))
        resource_id = nested[0] if nested else ""
    if not resource_id:
        return None
    system_id = str(record.get("system_id") or record.get("data_store") or record.get("service") or system_for(resource_id) or "")
    if not system_id:
        return None
    text = " ".join(str(value) for value in record.values() if value is not None)
    category = _category(record, category_hint) or _category_from_text(text)
    tokens = _tokens(text)
    cross_refs = set(RESOURCE_RE.findall(text)) - {resource_id}
    for key in ("source_resource_id", "customer_reference", "subject_reference", "lookup_key"):
        value = record.get(key)
        if value and RESOURCE_RE.fullmatch(str(value)):
            cross_refs.add(str(value))
        if value and USER_RE.fullmatch(str(value)):
            tokens.add(str(value).lower())
    presence, exposed, flow, restore = _state(record, text, tokens)
    retention = record.get("retention_until")
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
        ("service=account_service", "USER_PROFILE"),
        ("service=search_service", "SEARCH_INDEX_ENTRY"),
        ("service=analytics_platform", "ANALYTICS_PROFILE"),
        ("service=security_service", "SECURITY_AUDIT_LOG"),
        ("service=backup_service", "BACKUP_ARCHIVE"),
        ("service=integration_service", "DATA_FLOW"),
        ("service=export_service", "USER_EXPORT"),
        ("service=identity_service", "ACCOUNT_TOMBSTONE"),
        ("service=support_platform", "SUPPORT_MESSAGE"),
    ):
        if needle in lowered:
            return category
    return None


def _category(record: dict, hint: str) -> str | None:
    for value in record.values():
        if isinstance(value, str) and value in CATEGORIES:
            return value
    lowered = hint.lower()
    for name, category in (
        ("security_audit", "SECURITY_AUDIT_LOG"),
        ("deleted_customer", "ACCOUNT_TOMBSTONE"),
        ("tombstone", "ACCOUNT_TOMBSTONE"),
        ("analytics", "ANALYTICS_PROFILE"),
        ("search", "SEARCH_INDEX_ENTRY"),
        ("backup", "BACKUP_ARCHIVE"),
        ("export", "USER_EXPORT"),
        ("support", "SUPPORT_MESSAGE"),
        ("profile", "USER_PROFILE"),
        ("account", "USER_PROFILE"),
        ("data_flow", "DATA_FLOW"),
        ("connector", "DATA_FLOW"),
        ("legal_hold", "LEGAL_HOLD_RECORD"),
        ("marketing", "MARKETING_PROFILE"),
        ("email_delivery", "EMAIL_DELIVERY_LOG"),
        ("cache", "CACHE_ENTRY"),
    ):
        if name in lowered:
            return category
    return None


def _state(record: dict, text: str, tokens: set[str]) -> tuple[str, bool | None, str | None, str | None]:
    blob = text.upper()
    presence = "unknown"
    if any(token in blob for token in ("NOT_FOUND", "HTTP_STATUS=404", "STATUS_CODE=404", "ROWS=0")):
        presence = "absent"
    elif record.get("profile") is None and str(record.get("status_code")) == "404":
        presence = "absent"
    elif any(token in blob for token in ("IDENTIFIABLE", "ANONYMIZED", "REDACTED", "FOUND", "ROWS=1", "HTTP_STATUS=200")):
        presence = "present"
    elif tokens:
        presence = "present"

    exposed: bool | None = None
    if "ANONYMIZED" in blob or "REDACTED" in blob:
        exposed = False
        presence = "present"
    elif "IDENTIFIABLE" in blob:
        exposed = True
        presence = "present"
    elif presence == "present":
        exposed = bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or HASH_RE.search(text))

    flow = None
    if "enabled=true" in text.lower() or "DATA_FLOW | ACTIVE" in blob or str(record.get("state")) == "ACTIVE" and "data_flow" in text:
        flow = "active"
    if "enabled=false" in text.lower() or "DISABLED" in blob:
        flow = "disabled"

    restore = None
    if "restore_allowed=false" in text.lower() or "BLOCKED" in blob:
        restore = "blocked"
    elif "restore_allowed=true" in text.lower() or ("BACKUP_ARCHIVE" in blob and "ACTIVE" in blob):
        restore = "open"
    return presence, exposed, flow, restore


def _tokens(text: str) -> set[str]:
    found = {match.lower() for match in EMAIL_RE.findall(text)}
    found.update(match.lower() for match in USER_RE.findall(text))
    found.update(match.lower() for match in HASH_RE.findall(text))
    for phone in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", phone)
        if len(digits) >= 8:
            found.add(digits)
    return found


def _key_values(line: str) -> dict[str, str]:
    return {key: value for key, value in re.findall(r"([A-Za-z_]+)=([^\s]+)", line)}


def _mark_encoding(observations: list[Observation]) -> None:
    grouped: dict[tuple[str, str], list[Observation]] = {}
    for observation in observations:
        if observation.resource_id.startswith("account_"):
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
