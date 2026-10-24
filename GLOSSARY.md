# Glossary: Ghost Data Still Exists

Terms used in the HackerRank Orchestrate October 2026 challenge and the deletion-audit agent.

---

## Challenge & Output Terms

| Term | Definition |
| ---- | ---------- |
| **case_id** | Unique identifier for a deletion request and its corresponding output row. |
| **deletion_status** | Final decision for a case: `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`. |
| **steps_json** | Ordered JSON array of step objects describing findings, remediation, and verification. |
| **NOT_APPLICABLE** | The request does not authorize deletion (e.g., access, correction, export, marketing opt-out). `steps_json` must be `[]`. |
| **COMPLETE** | Every relevant copy has the required treatment, required retained records exist, and no active process can recreate prohibited data. Output contains only verification steps. |
| **INCOMPLETE** | At least one policy violation or recreation risk remains. Output must include findings, a full ordered remediation plan, and post-remediation verification steps. |
| **audit_at** | Timestamp cutoff. Only information available at or before this time may be used to decide the case. |
| **reported_status** | The deletion workflow’s claim (`COMPLETE`, `PARTIALLY_COMPLETE`, or `NOT_STARTED`). This is a claim, not proof. |
| **request_text** | Free-text message from the person. May be in any language. Used to determine whether deletion was actually requested. |

---

## Step Structure Terms

| Term | Definition |
| ---- | ---------- |
| **step_no** | Consecutive integer starting at 1. |
| **phase** | One of `FINDING`, `REMEDIATION`, or `VERIFICATION`. Must appear in that order. |
| **system_id** | Identifier of the system that holds the record or process (e.g., `account_service`, `backup_service`). |
| **resource_id** | Identifier of the specific record or process (e.g., `account_005`, `backup_4978`). |
| **operation** | The action or observation being reported. Must be one of the allowed operations. |
| **state** | The current or target state of the resource (e.g., `PRESENT`, `ABSENT`, `REDACTED`, `ACTIVE`, `BLOCKED`). |
| **evidence_id** | Reference to the participant-visible evidence that supports a finding or verification (`file_id`, `activity_id`, or `audit_id`). Empty string for proposed future work. |

---

## Allowed Operations

### FINDING
| Operation | State | Meaning |
| --------- | ----- | ------- |
| `REPORT_REMAINING_RECORD` | `PRESENT` | A record that should have been deleted still exists. |
| `REPORT_EXPOSED_PII` | `PRESENT` | A record may remain, but identifiers that policy requires to be redacted or anonymized are still exposed. |
| `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` | An active process can copy or recreate the user's data. |
| `REPORT_RESTORE_RISK` | `ACTIVE` | A backup or restore path can bring deleted data back. |

### REMEDIATION
| Operation | State | Meaning |
| --------- | ----- | ------- |
| `DISABLE_DATA_FLOW` | `DISABLED` | Stop a process that can copy or recreate the data. |
| `BLOCK_RESTORE` | `BLOCKED` | Prevent the affected backup from restoring the user's data. |
| `DELETE_RECORD` | `ABSENT` | Remove the entire record. |
| `REDACT_RECORD` | `REDACTED` | Keep the record but remove the identifying fields required by policy. |
| `ANONYMIZE_RECORD` | `ANONYMIZED` | Keep the record after irreversibly unlinking it from the user. |

### VERIFICATION
| Operation | State | Meaning |
| --------- | ----- | ------- |
| `VERIFY_RECORD_ABSENT` | `ABSENT` | Confirm that a record no longer exists. |
| `VERIFY_RECORD_PRESENT` | `PRESENT` | Confirm that a policy-required retained record still exists. |
| `VERIFY_RECORD_REDACTED` | `REDACTED` | Confirm that required identifying fields were removed. |
| `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` | Confirm that the record can no longer be linked to the user. |
| `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` | Confirm that the relevant data flow is inactive. |
| `VERIFY_RESTORE_BLOCKED` | `BLOCKED` | Confirm that the affected data cannot be restored. |

---

## Policy & Data Category Terms

| Term | Definition |
| ---- | ---------- |
| **deletion_rules.csv** | Defines the required action for each data category and condition (DELETE, REDACT, ANONYMIZE, RETAIN, or special tombstone handling). |
| **ACCOUNT_TOMBSTONE** | A retained record that keeps the stable internal `user_id` so other permitted records can still reference it, while direct identifiers (name, email, phone, email hash, etc.) must be removed. |
| **REDACT** | Keep the record but remove prohibited direct identifiers. |
| **ANONYMIZE** | Keep the record after irreversibly unlinking it from the user. |
| **RETAIN** | The record must be preserved (e.g., security audit logs within retention period, legal holds, or backups where restore can be blocked). |
| **PII** | Personally identifiable information (name, email, phone, email hash, and other direct identifiers). |

---

## Evidence & System Terms

| Term | Definition |
| ---- | ---------- |
| **evidence_files.csv** | Manifest that maps each `file_id` to its path, origin, and capture time. Does not identify which case a file concerns. |
| **file_id** | Participant-visible identifier for an evidence file (e.g., `evidence_54`). |
| **activity_id** | Identifier from `system_activity.csv` that can be cited as evidence. |
| **audit_id** | Identifier from audit-related evidence that can be cited. |
| **Replica** | A copy of a database (read replica, regional replica, reporting replica, failover replica). May lag behind the primary and contain data that was already deleted elsewhere. |
| **Active data flow** | A running process (sync, import, indexing, etc.) that can copy or recreate the user’s data. |
| **Restore risk** | A backup or archive from which the user’s data can still be restored. |
| **Ghost data** | Personal data that remains in the system after a deletion workflow reported completion. |

---

## Identity Terms

| Term | Definition |
| ---- | ---------- |
| **user_id** | Stable internal reference for an account. May remain in an account tombstone. |
| **Historical identifier** | An email, phone, name, or hash that the user previously had and that may still appear in older records or evidence. |
| **email hash** | Hashed version of an email address that may appear in analytics or other systems. |

---

## Submission & Evaluation Terms

| Term | Definition |
| ---- | ---------- |
| **output.csv** | The final prediction file written at the repository root. Must contain exactly 518 data rows sorted by `case_id`. |
| **code.zip** | Submission archive containing the runnable solution, prompts, configuration, `README.md`, and the `evaluation/` reports. Must not include `dataset/` or secrets. |
| **evaluation_report.md** | Required report with case-level accuracy, step-level accuracy, sequence accuracy, at least three custom evaluation cases, and notes on failures and improvements. |
| **usage_report.md** | Required report summarizing model providers, model names, call counts, token usage, and estimated cost for the full 518-case run. |
| **chat_transcript** | The root `log.txt` file generated by the coding agent (per AGENTS.md). |

---

## Other Useful Terms

| Term | Definition |
| ---- | ---------- |
| **Northstar Shop** | The fictional commerce platform used in the challenge scenario. |
| **Participant-facing data** | Everything under `dataset/`. This is the only data that may be used for predictions. |
| **Organizer-only files** | Truth files, golden answers, and generator internals that must never be used. |
| **Decoy** | Unrelated records or activity that appear in global data and must not be attributed to the subject. |
