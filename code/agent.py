"""Extract typed facts with a Grok model. The model does not choose status or steps."""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from evidence_index import EMAIL_RE, HASH_RE, PHONE_RE, RESOURCE_RE, USER_RE, Observation, _tokens

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
API_URL = "https://api.x.ai/v1/chat/completions"
ALLOWED_CATEGORIES = {
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


class ExtractionError(RuntimeError):
    """A required model call failed and no fallback answered."""


@dataclass
class Usage:
    provider: str
    model: str
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.estimated_cost_usd += other.estimated_cost_usd


@dataclass
class FactAgent:
    model: str
    fallbacks: list[str]
    api_key: str
    cache_path: Path
    usages: dict[str, Usage] = field(default_factory=dict)
    vision_skipped: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, cache_path: Path) -> "FactAgent":
        model = os.environ.get("DELETION_AUDIT_MODEL", "grok-4.7")
        if not model.startswith("grok-4"):
            raise ExtractionError(f"DELETION_AUDIT_MODEL must start with grok-4, got {model}")
        raw = os.environ.get("DELETION_AUDIT_FALLBACK_MODELS", "")
        fallbacks = [item.strip() for item in raw.split(",") if item.strip()]
        key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or ""
        return cls(model=model, fallbacks=fallbacks, api_key=key, cache_path=cache_path)

    def classify(self, text: str) -> bool | None:
        """Yes, no, or None when the call fails. None is not authorization."""
        prompt = (PROMPT_DIR / "classify_request.md").read_text(encoding="utf-8")
        try:
            answer, _model = self._complete(prompt + "\n\n" + text, images=None, cache_kind="classify", cache_body=text)
        except ExtractionError:
            raise
        word = answer.strip().lower().split()[0] if answer.strip() else ""
        if word.startswith("yes"):
            return True
        if word.startswith("no"):
            return False
        return None

    def extract_image(self, row: dict[str, str], path: Path) -> list[Observation]:
        return self._extract_file(row, path, kind="image")

    def extract_pdf(self, row: dict[str, str], path: Path) -> list[Observation]:
        return self._extract_file(row, path, kind="pdf")

    def _extract_file(self, row: dict[str, str], path: Path, kind: str) -> list[Observation]:
        if not self.api_key:
            self.vision_skipped.append(row["file_id"])
            return []
        prompt = (PROMPT_DIR / "extract_facts.md").read_text(encoding="utf-8")
        image = _data_url(path) if kind == "image" else None
        body = path.read_bytes()
        try:
            answer, _model = self._complete(prompt, images=[image] if image else None, cache_kind=kind, cache_body=body.hex())
        except ExtractionError as exc:
            self.vision_skipped.append(f"{row['file_id']}: {exc}")
            return []
        return _observations_from_facts(row, answer)

    def _complete(self, prompt: str, images: list[str] | None, cache_kind: str, cache_body: str) -> tuple[str, str]:
        models = [self.model, *self.fallbacks]
        last_error: Exception | None = None
        for model in models:
            cached = self._cache_get(model, cache_kind, cache_body)
            if cached is not None:
                self._note(model, 0, 0)
                return cached, model
            if not self.api_key:
                raise ExtractionError("model call required and no API key is set")
            try:
                text, usage = _post_chat(self.api_key, model, prompt, images)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ExtractionError) as exc:
                last_error = exc
                continue
            self._cache_put(model, cache_kind, cache_body, text)
            self._note(model, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            return text, model
        raise ExtractionError(f"model extraction failed: {last_error}")

    def _note(self, model: str, input_tokens: int, output_tokens: int) -> None:
        usage = self.usages.setdefault(model, Usage("xai", model))
        usage.calls += 1
        usage.input_tokens += int(input_tokens or 0)
        usage.output_tokens += int(output_tokens or 0)
        usage.estimated_cost_usd += (int(input_tokens or 0) * 3.0 + int(output_tokens or 0) * 15.0) / 1_000_000

    def _cache_get(self, model: str, kind: str, body: str) -> str | None:
        if not self.cache_path.exists():
            return None
        with sqlite3.connect(self.cache_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS facts (model TEXT, kind TEXT, body TEXT, answer TEXT, PRIMARY KEY (model, kind, body))")
            row = connection.execute("SELECT answer FROM facts WHERE model=? AND kind=? AND body=?", (model, kind, body)).fetchone()
        return None if row is None else row[0]

    def _cache_put(self, model: str, kind: str, body: str, answer: str) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.cache_path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS facts (model TEXT, kind TEXT, body TEXT, answer TEXT, PRIMARY KEY (model, kind, body))")
            connection.execute("INSERT OR REPLACE INTO facts VALUES (?, ?, ?, ?)", (model, kind, body, answer))


def _post_chat(api_key: str, model: str, prompt: str, images: list[str] | None) -> tuple[str, dict]:
    content: list[dict] | str
    if images:
        content = [{"type": "text", "text": prompt}]
        for image in images:
            if image:
                content.append({"type": "image_url", "image_url": {"url": image}})
    else:
        content = prompt
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ExtractionError(f"HTTP {exc.code}: {detail}") from exc
    text = body["choices"][0]["message"]["content"]
    return text, body.get("usage") or {}


def _data_url(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _observations_from_facts(row: dict[str, str], answer: str) -> list[Observation]:
    start = answer.find("{")
    end = answer.rfind("}")
    if start == -1 or end == -1:
        raise ExtractionError("model did not return JSON facts")
    try:
        payload = json.loads(answer[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ExtractionError("model returned invalid JSON") from exc
    observations: list[Observation] = []
    for item in payload.get("records") or []:
        resource_id = str(item.get("resource_id") or "")
        if not RESOURCE_RE.fullmatch(resource_id):
            continue
        category = str(item.get("category") or "")
        if category not in ALLOWED_CATEGORIES:
            category = ""
        identifiers = item.get("identifiers") or {}
        tokens = set()
        for email in identifiers.get("emails") or []:
            tokens.update(match.lower() for match in EMAIL_RE.findall(str(email)))
        for user_id in identifiers.get("user_ids") or []:
            tokens.update(match.lower() for match in USER_RE.findall(str(user_id)))
        for email_hash in identifiers.get("email_hashes") or []:
            tokens.update(match.lower() for match in HASH_RE.findall(str(email_hash)))
        for phone in identifiers.get("phones") or []:
            digits = "".join(char for char in str(phone) if char.isdigit())
            if len(digits) >= 8:
                tokens.add(digits)
        for name in identifiers.get("names") or []:
            if str(name).strip():
                tokens.add(str(name).strip().lower())
        presence = str(item.get("presence") or "unknown")
        if presence not in {"present", "absent", "unknown"}:
            presence = "unknown"
        flow = item.get("flow") or None
        restore = item.get("restore") or None
        exposed = item.get("direct_identifiers_exposed")
        observations.append(
            Observation(
                file_id=row["file_id"],
                captured_at=row["captured_at"],
                copy_key=f"vision:{resource_id}",
                system_id=str(item.get("system_id") or "") or _system(resource_id),
                resource_id=resource_id,
                category=category or None,
                presence=presence,
                exposed=None if exposed is None else bool(exposed),
                flow=flow if flow in {"active", "disabled"} else None,
                restore=restore if restore in {"open", "blocked"} else None,
                retention_until=str(item.get("retention_until") or "") or None,
                hold_active=None,
                tokens=tokens or _tokens(json.dumps(item)),
            )
        )
    return observations


def _system(resource_id: str) -> str:
    from constants import system_for

    return system_for(resource_id) or ""
