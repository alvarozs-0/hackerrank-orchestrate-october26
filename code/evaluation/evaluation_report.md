# Evaluation report

The public sample gate is `python code/main.py --samples`. It scores `dataset/sample_deletion_requests.csv` against `dataset/sample_output.csv`. JSON key order and whitespace are ignored. Array order is not.

## Public sample

| Metric | Result |
| --- | --- |
| Cases decided | 32/32 |
| Case-level status accuracy | 32/32 (100%) |
| Exact step-sequence accuracy | 15/32 (46.9%) |
| Aligned field accuracy | 986/1158 (85.1%) |

Field accuracy compares `phase`, `operation`, `state`, `system_id`, `resource_id`, and `evidence_id` on steps aligned by position. A missing or extra step counts as six field misses. Status is scored separately.

The 15 exact rows are the cases whose relevant records are tied to the subject by an identifier in an eligible file, a same-trace lookup, one same-row cross-reference, or the file-local account-id encoding.

## Custom cases

These cases are not inserted into `dataset/deletion_requests.csv`.

1. Non-deletion. Request text: "Please correct the phone number on my account. This is not a deletion." Expected status: `NOT_APPLICABLE`. Expected steps: `[]`. The rule classifier returns no, so no deletion work is planned.
2. Exposed tombstone. An `ACCOUNT_TOMBSTONE` row is still present and still contains an email. Expected status: `INCOMPLETE`. Expected finding: `REPORT_EXPOSED_PII` / `PRESENT`, remediation `REDACT_RECORD` / `REDACTED`, verification `VERIFY_RECORD_REDACTED`. The stable `user_id` is not treated as prohibited PII. There is no fifth tombstone operation.
3. Recreation path. A linked connector has `enabled=true`, and the account lookup is a 404. Expected status: `INCOMPLETE`. Expected finding: `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE` before any record change, then `DISABLE_DATA_FLOW`, then verification that the account is absent and the flow is disabled.

## Failures found

- Eleven public cases blocked because a linked record had no category. The category was printed as a collection, table, or event name (`connectors`, `security_audit_events`, `profile_lookup_completed`), not as the enum string.
- Lookup traces split the identifier and the resource id across lines. Joining on `trace_id` recovered those links. A started line is not a presence proof.
- A deletion-worker activity row with no identifier was being treated as a resource. That blocked `object_19` and `tombstone_17`, which the sample does not include. Activity is now a link only when a file observation of that resource also exists.
- `support_001` is a PDF attachment. Text extraction finds the resource id and the email. Vision is not used when the text layer is usable.
- File-local encoding still derives `account_061` when no account is linked. The sample wants `account_3960` for that person. The eligible files do not tie `account_3960` to the subject. `audit_record_4902` is in a file whose manifest time is after `audit_at`, so it is not eligible.
- Several sample verification rows name an account, an anonymized analytics profile, or an audit record that has no identifier in any file captured at or before `audit_at`. Examples: `analytics_901`, `account_4857`, `account_5521`, `audit_record_6645`. A later snapshot does tie some of those ids to the subject, but its manifest time is after `audit_at`. Using it would change the case. Those rows are omitted rather than guessed.
- `case_17` had an older 404 for a different account id. The later lookup is the account of record when every linked account lookup is an absence.

## Improvements made

- Deterministic policy engine remains the only writer of status and steps.
- Evidence is parsed once per run from SQL, JSON, logs, text, and PDF text.
- A Grok fact extractor is wired for screenshots, textless PDF pages, and unmatched request wording. Prompts ask for facts or yes/no. They do not ask for a status or an operation.
- Cache key and usage ledger record the model that answered. Fallback models run only after the primary call fails.
- The full command still refuses to write `output.csv` when a case cannot be decided. The 518-case run has not been started, because 17 public step sequences still disagree with the sample.
