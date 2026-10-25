"""Decide whether request_text is a deletion request.

Known wording is a rule. Unmatched wording returns None so the caller can
fail closed or ask a model. A model must not be the first classifier.
"""

from __future__ import annotations

import re

_DELETION = re.compile(
    r"("
    r"\bdelet(?:e|ed|ion|ing)\b|"
    r"\beras(?:e|ure|ing)\b|"
    r"\bclos(?:e|ed|ing)\b.{0,40}\baccount\b|"
    r"\baccount\b.{0,40}\bclos(?:e|ed|ing)\b|"
    r"\bremove\b.{0,50}\b(?:profile|account|personal|details|data|records|result|search)\b|"
    r"\belimin(?:ar|ación|acion)\b|"
    r"\bexclus[aã]o\b|\bexcluir\b|"
    r"\bsuppression\b|\bsupprimer\b|"
    r"削除|삭제|"
    r"\bpermanent(?:ly)?\b.{0,40}\b(?:delet|eras|remov)"
    r")",
    re.IGNORECASE,
)

_INSPECT_DELETION = re.compile(
    r"("
    r"\binspect\b.{0,80}\b(?:account|analytics|removed|deleted)\b|"
    r"\bconfirm\b.{0,80}\b(?:gone|deleted|removed|cannot identify)\b|"
    r"\bverify\b.{0,80}\b(?:deleted|deletion|account was)\b|"
    r"\bcheck\b.{0,40}\b(?:latest state|whether)\b.{0,40}\b(?:gone|removed|deleted)\b|"
    r"\bwhether\b.{0,60}\b(?:removed|deleted)\b"
    r")",
    re.IGNORECASE,
)

_NON_DELETION = re.compile(
    r"("
    r"\bcorrect\b.{0,40}\b(?:phone|surname|name|email)\b|"
    r"\bmisspell|"
    r"\bpromotional\b|\bmarketing\b.{0,30}\b(?:only|list|email)\b|"
    r"\bopt[- ]?out\b|\bunsubscribe\b|"
    r"\bportable copy\b|\bdownload\b.{0,30}\bcopy\b|"
    r"\breset\b.{0,20}\b(?:login|password)\b|"
    r"\bwhat personal information\b|"
    r"\binvoices\b|"
    r"\bchange\b.{0,30}\bemail\b|"
    r"\bdo not delete\b|\bnot an erasure\b|\bnot a deletion\b|"
    r"\bkeep the account\b|\bkeep using\b"
    r")",
    re.IGNORECASE,
)


def is_deletion_request(text: str) -> bool | None:
    """True, False, or None when the wording matches no known pattern."""
    if _DELETION.search(text) or _INSPECT_DELETION.search(text):
        return True
    if _NON_DELETION.search(text):
        return False
    return None
