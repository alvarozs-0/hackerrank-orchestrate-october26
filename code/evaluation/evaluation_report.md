# Evaluation report

The public sample gate is `python code/main.py --samples`. It scores `dataset/sample_deletion_requests.csv` against `dataset/sample_output.csv`. JSON key order and whitespace are ignored. Array order is not.

## Public sample

| Metric | Result |
| --- | --- |
| Cases decided | 32/32 |
| Case-level status accuracy | 32/32 (100%) |
| Exact step-sequence accuracy | 13/32 (40.6%) |
| Aligned field accuracy | 950/1194 (79.6%) |

Field accuracy compares `phase`, `operation`, `state`, `system_id`, `resource_id`, and `evidence_id` on steps aligned by position. A missing or extra step counts as six field misses. Status is scored separately.

The misses are resources named by the sample that have no identifier in a file captured at or before `audit_at`. Those rows were not guessed. A later snapshot sometimes ties the id to the person, but its manifest time is after the cutoff.

## Full file

`python code/main.py` wrote root `output.csv` with 518 rows, sorted by `case_id`.

| Status | Rows |
| --- | --- |
| INCOMPLETE | 332 |
| COMPLETE | 180 |
| NOT_APPLICABLE | 6 |

Fifteen deletion requests had no eligible linked record. They were written `COMPLETE` with `steps_json` `[]` rather than omitted: `case_35`, `case_39`, `case_52`, `case_53`, `case_55`, and `case_433` through `case_442`. Eleven screenshots were not read in that run.

## Custom cases

These cases are not inserted into `dataset/deletion_requests.csv`.

1. Non-deletion. Request text: "Please correct the phone number on my account. This is not a deletion." Expected status: `NOT_APPLICABLE`. Expected steps: `[]`. The rule classifier returns no, so no deletion work is planned.
2. Exposed tombstone. An `ACCOUNT_TOMBSTONE` row is still present and still contains an email. Expected status: `INCOMPLETE`. Expected finding: `REPORT_EXPOSED_PII` / `PRESENT`, remediation `REDACT_RECORD` / `REDACTED`, verification `VERIFY_RECORD_REDACTED`. The stable `user_id` is not treated as prohibited PII. There is no fifth tombstone operation.
3. Recreation path. A linked connector has `enabled=true`, and the account lookup is a 404. Expected status: `INCOMPLETE`. Expected finding: `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE` before any record change, then `DISABLE_DATA_FLOW`, then verification that the account is absent and the flow is disabled.

## Failures found

- A model HTTP 403 during evidence reading was reported as `case_33` because that row is first. The request text itself did not need a model.
- Lookup traces split the identifier and the resource id across lines. Joining on `trace_id` recovered those links. A started line is not a presence proof.
- Collection and event names such as `support_conversations` and `profile_lookup_completed` were not mapped to a deletion-rules category, so linked records blocked the run.
- Complete cases left `step_no` at 0. They are now numbered from 1.
- Several sample verification rows name an account, an anonymized analytics profile, or an audit record with no identifier in any eligible file. Examples: `analytics_901`, `account_4857`, `account_5521`. Those were omitted rather than guessed.

## Improvements made

- The policy engine remains the only writer of status and steps.
- Evidence is parsed once per run from SQL, JSON, logs, text, and PDF text.
- A Grok fact extractor is wired for screenshots, textless PDF pages, and unmatched request wording. Prompts ask for facts or yes/no. They do not ask for a status or an operation.
- A forbidden vision call no longer aborts the dataset. The run continues on text evidence and still writes one row per case.
