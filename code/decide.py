"""Turn a typed case state into deletion_status and steps_json."""

from __future__ import annotations

from dataclasses import dataclass, field

from constants import (
    ANONYMIZE_CATEGORIES,
    DELETE_CATEGORIES,
    OPERATION_STATE,
    PHASE_OPERATIONS,
    PHASE_ORDER,
    REDACT_CATEGORIES,
    RETAIN_CATEGORIES,
    system_for,
)
from evidence_index import ActivityLink, Observation
from identity import Subject

STEP_KEYS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")


@dataclass
class ResourceView:
    system_id: str
    resource_id: str
    category: str | None
    presence: str
    exposed: bool | None
    flow: str | None
    restore: str | None
    retention_until: str | None
    evidence_id: str
    captured_at: str
    items: list[Observation] = field(default_factory=list)


@dataclass
class CaseResult:
    status: str
    steps: list[dict[str, str | int]]
    blockers: list[str] = field(default_factory=list)


def decide_case(
    audit_at: str,
    subject: Subject,
    observations: list[Observation],
    links: list[ActivityLink],
) -> CaseResult:
    eligible = [item for item in observations if item.captured_at <= audit_at]
    linked_ids = _prefer_latest_absent_account(_linked_ids(subject, eligible, links, audit_at), eligible)
    encoded: dict[str, tuple[str, str]] = {}
    if not any(resource_id.startswith("account_") for resource_id in linked_ids):
        encoded = _encoded_absences(subject, eligible)
        linked_ids.update(encoded)
    if not linked_ids:
        return CaseResult("", [], ["no grounded resource"])

    views = _views(linked_ids, eligible, encoded)
    missing = [resource_id for resource_id, view in views.items() if view.category is None and view.flow is None and view.restore is None]
    if missing:
        return CaseResult("", [], [f"no printed category: {', '.join(sorted(missing)[:8])}"])

    violations: list[tuple[str, ResourceView]] = []
    verifications: list[tuple[str, ResourceView]] = []
    for view in views.values():
        kind = _classify(view, audit_at)
        if kind is None:
            return CaseResult("", [], [f"unmatched rule: {view.resource_id} {view.category}"])
        finding, verification = kind
        if finding:
            violations.append((finding, view))
        verifications.append((verification, view))

    if not violations:
        steps = _steps("VERIFICATION", verifications, cite=True)
        return CaseResult("COMPLETE", steps, [])
    steps = []
    steps.extend(_steps("FINDING", violations, cite=True))
    steps.extend(_steps("REMEDIATION", [( _remediation(operation), view) for operation, view in violations], cite=False))
    steps.extend(_steps("VERIFICATION", verifications, cite=False))
    for number, step in enumerate(steps, start=1):
        step["step_no"] = number
    return CaseResult("INCOMPLETE", steps, [])


def _prefer_latest_absent_account(linked_ids: set[str], observations: list[Observation]) -> set[str]:
    """A later profile lookup replaces an older miss for a different account id."""
    accounts = [item for item in observations if item.resource_id in linked_ids and item.resource_id.startswith("account_")]
    latest: dict[str, Observation] = {}
    for item in accounts:
        current = latest.get(item.resource_id)
        if current is None or item.captured_at >= current.captured_at:
            latest[item.resource_id] = item
    if len(latest) < 2 or any(item.presence != "absent" for item in latest.values()):
        return linked_ids
    winner = max(latest.values(), key=lambda item: (item.captured_at, item.file_id))
    return {resource_id for resource_id in linked_ids if not resource_id.startswith("account_") or resource_id == winner.resource_id}


def _linked_ids(subject: Subject, observations: list[Observation], links: list[ActivityLink], audit_at: str) -> set[str]:
    tokens = subject.tokens()
    observed = {item.resource_id for item in observations}
    direct = {item.resource_id for item in observations if item.tokens & tokens}
    for link in links:
        if link.event_time <= audit_at and link.tokens & tokens and link.resource_id in observed:
            direct.add(link.resource_id)
    one_hop = set(direct)
    for item in observations:
        if item.cross_refs & direct:
            one_hop.add(item.resource_id)
    return one_hop


def _encoded_absences(subject: Subject, observations: list[Observation]) -> dict[str, tuple[str, str]]:
    """File-local account encoding. Cite the latest snapshot that uses the encoding and omits the subject."""
    number = subject.user_id.split("_")[-1]
    derived = f"account_{number.zfill(3)}"
    copies: dict[tuple[str, str], list[Observation]] = {}
    for item in observations:
        if item.encodes_user and item.resource_id.startswith("account_"):
            copies.setdefault((item.file_id, item.copy_key), []).append(item)
    chosen: tuple[str, str] | None = None
    for group in copies.values():
        present_users = {token for item in group for token in item.tokens if token.startswith("user_")}
        if subject.user_id.lower() in present_users:
            continue
        file_id = group[0].file_id
        captured_at = max(item.captured_at for item in group)
        if chosen is None or captured_at >= chosen[1]:
            chosen = (file_id, captured_at)
    if chosen is None:
        return {}
    return {derived: chosen}


def _views(
    resource_ids: set[str],
    observations: list[Observation],
    encoded: dict[str, tuple[str, str]],
) -> dict[str, ResourceView]:
    grouped: dict[str, list[Observation]] = {}
    for item in observations:
        if item.resource_id in resource_ids:
            grouped.setdefault(item.resource_id, []).append(item)
    views: dict[str, ResourceView] = {}
    for resource_id in resource_ids:
        items = grouped.get(resource_id, [])
        if not items:
            system_id = system_for(resource_id) or ""
            file_id, captured_at = encoded.get(resource_id, ("", ""))
            category = "USER_PROFILE" if resource_id.startswith("account_") else None
            synthetic = Observation(
                file_id,
                captured_at,
                "encoded-absence",
                system_id,
                resource_id,
                category,
                "absent",
                False,
                None,
                None,
                None,
                None,
            )
            views[resource_id] = ResourceView(
                system_id, resource_id, category, "absent", False, None, None, None, file_id, captured_at, [synthetic]
            )
            continue
        items.sort(key=lambda item: (item.captured_at, item.file_id))
        categories = {item.category for item in items if item.category}
        category = next(iter(categories)) if len(categories) == 1 else (None if categories else None)
        if len(categories) > 1:
            category = _preferred_category(categories)
        presences = {item.presence for item in items}
        if "present" in presences:
            presence = "present"
        elif "absent" in presences:
            presence = "absent"
        else:
            presence = "unknown"
        exposed = any(item.presence == "present" and item.exposed for item in items)
        if presence != "present":
            exposed = False
        flows = {item.flow for item in items if item.flow}
        restores = {item.restore for item in items if item.restore}
        flow = "active" if "active" in flows else ("disabled" if "disabled" in flows else None)
        restore = "open" if "open" in restores else ("blocked" if "blocked" in restores else None)
        retention = next((item.retention_until for item in reversed(items) if item.retention_until), None)
        chosen = items[-1]
        views[resource_id] = ResourceView(
            chosen.system_id or system_for(resource_id) or "",
            resource_id,
            category,
            presence,
            exposed,
            flow,
            restore,
            retention,
            chosen.file_id,
            chosen.captured_at,
            items,
        )
    return views


def _classify(view: ResourceView, audit_at: str) -> tuple[str | None, str] | None:
    if view.category == "DATA_FLOW" or view.flow:
        if view.flow == "active":
            return "REPORT_ACTIVE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"
        if view.flow == "disabled":
            return None, "VERIFY_DATA_FLOW_DISABLED"
        return None
    if view.category == "BACKUP_ARCHIVE" or view.restore:
        if view.restore == "open" or (view.presence == "present" and view.restore != "blocked"):
            return "REPORT_RESTORE_RISK", "VERIFY_RESTORE_BLOCKED"
        if view.restore == "blocked":
            return None, "VERIFY_RESTORE_BLOCKED"
        return None
    if view.category in DELETE_CATEGORIES:
        if view.presence == "present":
            return "REPORT_REMAINING_RECORD", "VERIFY_RECORD_ABSENT"
        if view.presence == "absent":
            return None, "VERIFY_RECORD_ABSENT"
        return None
    if view.category in REDACT_CATEGORIES:
        if view.presence == "present" and view.exposed:
            return "REPORT_EXPOSED_PII", "VERIFY_RECORD_REDACTED"
        if view.presence == "present":
            return None, "VERIFY_RECORD_REDACTED"
        return None
    if view.category in ANONYMIZE_CATEGORIES:
        if view.presence == "present" and view.exposed:
            return "REPORT_EXPOSED_PII", "VERIFY_RECORD_ANONYMIZED"
        if view.presence == "present":
            return None, "VERIFY_RECORD_ANONYMIZED"
        return None
    if view.category in RETAIN_CATEGORIES:
        if view.category == "LEGAL_HOLD_RECORD" and view.hold_active is None:
            return None
        if view.category == "SECURITY_AUDIT_LOG" and view.retention_until and view.retention_until < audit_at:
            return None
        if view.presence == "present":
            return None, "VERIFY_RECORD_PRESENT"
        return None
    return None


def _preferred_category(categories: set[str]) -> str | None:
    ranked = [
        "SUPPORT_ATTACHMENT",
        "SUPPORT_MESSAGE",
        "ACCOUNT_TOMBSTONE",
        "USER_PROFILE",
        "SEARCH_INDEX_ENTRY",
        "ANALYTICS_PROFILE",
        "DATA_FLOW",
        "BACKUP_ARCHIVE",
        "SECURITY_AUDIT_LOG",
        "USER_EXPORT",
        "SECONDARY_IDENTIFIER",
    ]
    for category in ranked:
        if category in categories:
            return category
    return sorted(categories)[0]


def _cite(operation: str, view: ResourceView) -> str:
    def proves(item: Observation) -> bool:
        if operation == "REPORT_REMAINING_RECORD":
            return item.presence == "present"
        if operation == "REPORT_EXPOSED_PII":
            return item.presence == "present" and bool(item.exposed)
        if operation == "REPORT_ACTIVE_DATA_FLOW":
            return item.flow == "active"
        if operation == "REPORT_RESTORE_RISK":
            return item.restore == "open"
        if operation == "VERIFY_RECORD_ABSENT":
            return item.presence == "absent"
        if operation == "VERIFY_RECORD_PRESENT":
            return item.presence == "present"
        if operation in {"VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED"}:
            return item.presence == "present" and not item.exposed
        if operation == "VERIFY_DATA_FLOW_DISABLED":
            return item.flow == "disabled"
        if operation == "VERIFY_RESTORE_BLOCKED":
            return item.restore == "blocked"
        return False

    proving = [item for item in view.items if proves(item) and item.file_id]
    if not proving:
        return view.evidence_id
    latest = max(item.captured_at for item in proving)
    tied = sorted((item for item in proving if item.captured_at == latest), key=lambda item: item.file_id)
    return tied[0].file_id


def _remediation(finding: str) -> str:
    return {
        "REPORT_REMAINING_RECORD": "DELETE_RECORD",
        "REPORT_EXPOSED_PII": "REDACT_RECORD",
        "REPORT_ACTIVE_DATA_FLOW": "DISABLE_DATA_FLOW",
        "REPORT_RESTORE_RISK": "BLOCK_RESTORE",
    }[finding]


def _steps(phase: str, pairs: list[tuple[str, ResourceView]], cite: bool) -> list[dict[str, str | int]]:
    order = {name: index for index, name in enumerate(PHASE_OPERATIONS[phase])}
    pairs = sorted(pairs, key=lambda pair: (order[pair[0]], pair[1].system_id, pair[1].resource_id))
    steps = []
    for operation, view in pairs:
        if phase == "REMEDIATION" and operation == "REDACT_RECORD" and view.category in ANONYMIZE_CATEGORIES:
            operation = "ANONYMIZE_RECORD"
        steps.append(
            {
                "step_no": 0,
                "phase": phase,
                "system_id": view.system_id,
                "resource_id": view.resource_id,
                "operation": operation,
                "state": OPERATION_STATE[operation],
                "evidence_id": _cite(operation, view) if cite else "",
            }
        )
    steps.sort(key=lambda step: (PHASE_ORDER[step["phase"]], order[step["operation"]], step["system_id"], step["resource_id"]))
    return steps
