"""Resolve a request email to the subject and their identifiers."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path


def digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


@dataclass
class Subject:
    user_id: str
    emails: set[str] = field(default_factory=set)
    phones: set[str] = field(default_factory=set)
    hashes: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)

    def tokens(self) -> set[str]:
        found = {self.user_id.lower()}
        found.update(email.lower() for email in self.emails if email)
        found.update(phone for phone in self.phones if len(phone) >= 8)
        found.update(value.lower() for value in self.hashes if value)
        found.update(name.lower() for name in self.names if name)
        return found


@dataclass
class IdentityIndex:
    by_email: dict[str, str]
    subjects: dict[str, Subject]

    def resolve(self, email: str) -> Subject | None:
        user_id = self.by_email.get(email.lower())
        if user_id is None:
            return None
        return self.subjects[user_id]


def load_identities(dataset: Path) -> IdentityIndex:
    by_email: dict[str, str] = {}
    subjects: dict[str, Subject] = {}

    with (dataset / "user_identities.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            subject = subjects.setdefault(row["user_id"], Subject(row["user_id"]))
            if row["email"]:
                subject.emails.add(row["email"])
                by_email[row["email"].lower()] = row["user_id"]
            phone = digits(row["phone"])
            if phone:
                subject.phones.add(phone)
            if row["email_hash"]:
                subject.hashes.add(row["email_hash"].lower())
            if row["name"]:
                subject.names.add(row["name"])

    with (dataset / "user_audit_log.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            subject = subjects.setdefault(row["user_id"], Subject(row["user_id"]))
            field_name = row["field_name"]
            for value in (row["old_value"], row["new_value"]):
                if not value:
                    continue
                if field_name == "email":
                    subject.emails.add(value)
                    by_email.setdefault(value.lower(), row["user_id"])
                elif field_name == "phone":
                    phone = digits(value)
                    if phone:
                        subject.phones.add(phone)
                elif field_name == "email_hash":
                    subject.hashes.add(value.lower())
                elif field_name == "name":
                    subject.names.add(value)

    return IdentityIndex(by_email, subjects)
