# Deletion-audit agent

The contract remains the problem statement and the agent instructions for this challenge. This spec chooses only what that contract leaves open. If they disagree, the contract wins.

## Problem Statement

Northstar Shop reported deletions as complete while ghost data remained in replicas, logs, support records, search indexes, analytics, exports, archives, and backups. A person can also ask for something other than deletion. The privacy auditor needs one decision per case at `audit_at`: the deletion is `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`, with an ordered `steps_json` that a contest grader can score. `reported_status` is a claim, not proof. A wrong link is worse than a missing resource, and a guessed row is worse than no file.

## Solution

The privacy auditor runs one terminal command over the participant-facing dataset. The command resolves whether the text is a deletion request, reconstructs the subject's identifiers, follows only grounded links, applies the deletion rules, and writes one row per `case_id`. A model may extract typed facts. It does not choose `deletion_status` or write `steps_json`. If a required fact or rule is missing, the command exits non-zero and writes no output file.

## User Stories

1. As a privacy auditor, I want every case in the evaluation set to produce exactly one output row, so that the contest grader can score a complete file.
2. As a privacy auditor, I want the rows sorted by `case_id`, so that the output matches the required order.
3. As a privacy auditor, I want `deletion_status` to be only `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`, so that I do not invent a status.
4. As a privacy auditor, I want `steps_json` to be a JSON array, so that the contest grader can parse it.
5. As a privacy auditor, I want step numbers to start at 1 and increase by one, so that array order is unambiguous.
6. As a privacy auditor, I want phases in the order finding, remediation, then verification, so that the plan is safe to execute.
7. As a privacy auditor, I want steps inside a phase ordered by the operation table, then system, then resource, so that two runs produce the same sequence.
8. As a person, I want a request that asks to delete, erase, or close my account treated as a deletion request, so that my deletion is actually audited.
9. As a person, I want that decision to be the same in any language, so that a French, Spanish, Portuguese, Japanese, or Korean deletion request is not dropped.
10. As a person, I want a request that asks to inspect, confirm, or verify a deletion treated as a deletion request, so that a status check is not mistaken for a non-deletion.
11. As a person, I want a request that both corrects a detail and asks for deletion treated as a deletion request, so that the deletion ask is not ignored.
12. As a person, I want a request that only asks for access, correction, export, a marketing opt-out, or a login reset treated as `NOT_APPLICABLE`, so that data is not deleted without authorization.
13. As a person, I want `NOT_APPLICABLE` to carry an empty step list, so that no deletion work is implied.
14. As a privacy auditor, I want known wording classified by rule, so that the common templates do not depend on a model.
15. As a privacy auditor, I want unmatched wording sent to a model only for a yes or no, so that an uncertain answer does not become authorization.
16. As a privacy auditor, I want a model "no" or an uncertain answer to be `NOT_APPLICABLE`, so that authorization is not invented.
17. As a privacy auditor, I want the request email matched to a current or historical identifier, so that an old address still finds the subject.
18. As a privacy auditor, I want the subject to include `user_id`, emails, phones, names, and email hashes, so that older copies can still be linked.
19. As a privacy auditor, I want a resource included only through a grounded link, so that another person's account is not attributed to this subject.
20. As a privacy auditor, I want one same-row cross-reference to count as a grounded link, so that a search row pointing at the subject's account is included.
21. As a privacy auditor, I want a second hop ignored, so that neighbors of neighbors stay decoys.
22. As a privacy auditor, I want a deletion-worker timestamp ignored as a link, so that the nearest activity row is not treated as identity.
23. As a privacy auditor, I want the account-id encoding used only when that snapshot's own rows encode the user number and no other account is already linked, so that `account_001` can be derived for an omitted subject without inventing `account_061` for someone else.
24. As a privacy auditor, I want an unlinked resource omitted even if a sample names it, so that `analytics_901` and `account_4857` are not guessed.
25. As a privacy auditor, I want only evidence and activity at or before `audit_at`, so that later captures cannot change the case.
26. As a privacy auditor, I want the file's manifest capture time to be the cutoff, so that a nested older timestamp inside a later file does not make that file eligible.
27. As a privacy auditor, I want two tables in one SQL file treated as two copies, so that a live replica is not cancelled by an absent primary.
28. As a privacy auditor, I want absence proved by an explicit miss or by omission from the snapshot that should hold the record, so that a missing row is evidence.
29. As a privacy auditor, I want a printed category to beat the resource prefix, so that a support row can be a message or an attachment without guessing from `support_`.
30. As a privacy auditor, I want a resource prefix to determine the system only, so that category and system are not collapsed.
31. As a privacy auditor, I want a missing printed category to stop the run, so that a guessed category cannot become a step.
32. As a privacy auditor, I want a `DELETE` record that is still present reported as a remaining record, so that ghost data is named.
33. As a privacy auditor, I want a `REDACT` or `ANONYMIZE` record that still has direct identifiers reported as exposed PII, so that a tombstone with an email is not described as a record to delete.
34. As a privacy auditor, I want a compliant `RETAIN` record to produce no finding, so that a required security audit is not scheduled for deletion.
35. As a privacy auditor, I want an active copy process reported as an active data flow, so that sync cannot recreate deleted data.
36. As a privacy auditor, I want a restorable backup reported as a restore risk, so that the archive is blocked before records are changed.
37. As a privacy auditor, I want an account tombstone kept as a redaction, so that the permitted identifier remains and name, email, phone, and email hash are removed.
38. As a privacy auditor, I want no fifth tombstone operation, so that the step list stays inside the contract.
39. As a privacy auditor, I want a present security audit with no supplied expiry treated as still inside the retention period, so that a handover line without `retention_until` is not a crash.
40. As a privacy auditor, I want an explicit `retention_until` before `audit_at` to stop the run, so that an expired audit is not silently deleted or silently kept.
41. As a privacy auditor, I want a missing legal-hold flag to stop the run, so that a hold is not assumed active or inactive.
42. As a privacy auditor, I want a conditional retain rule that does not apply, and no other rule, to stop the run, so that an invented `DELETE` is not applied to an old security log.
43. As a privacy auditor, I want remediation to repeat only the findings, in operation-table order, so that data flows are disabled and restores blocked before records change.
44. As a privacy auditor, I want an incomplete case to verify the required end state of every relevant record and risk, including ones that were already compliant, so that the checklist proves the deletion after remediation.
45. As a privacy auditor, I want remediation and future verification to carry an empty evidence id, so that proposed work is not cited as if it already happened.
46. As a privacy auditor, I want a complete case to contain only verification steps, so that no finding or remediation is implied.
47. As a privacy auditor, I want a finding or a complete verification to cite a file when a file captured at or before `audit_at` proves the step, so that the contest grader sees participant-visible proof.
48. As a privacy auditor, I want several proving files reduced to the latest capture time, then the lowest file id, so that citation is a pure function.
49. As a privacy auditor, I want an activity id or audit id cited only when no eligible file proves the step, so that a file wins over a claim.
50. As a privacy auditor, I want the latest-file rule to be a citation tie-break only, so that an older non-compliant copy is not discarded.
51. As a privacy auditor, I want `reported_status` and activity results ignored as proof of state, so that a workflow claim cannot hide ghost data.
52. As a privacy auditor, I want all evidence parsed once and then queried per case, so that the same file is not reread for every subject.
53. As a privacy auditor, I want extracted facts cached in local SQLite, so that a second run does not repeat parsing or vision.
54. As a privacy auditor, I want PDF text extracted first, so that a text layer is not sent to vision.
55. As a privacy auditor, I want vision used only for screenshots and for PDF pages with no usable text, so that cost stays on artifacts that have no text.
56. As a privacy auditor, I want model extraction limited to identifiers, system, resource, a printed category, and a state observation, so that the model cannot return a verdict.
57. As a privacy auditor, I want the primary model to be any Grok 4 or later id from the environment, defaulting to `grok-4.7`, so that the graded path is not pinned to one build and is not a non-Grok model.
58. As a privacy auditor, I want fallback models to run only when the primary call fails, from an environment list that is empty by default, so that a cheap model is not silently preferred.
59. As a privacy auditor, I want the cache key and the usage report to record the model that actually answered, so that a fallback is visible.
60. As a privacy auditor, I want a failed required extraction, with no fallback answer, to exit non-zero and write no output file, so that a partial file cannot be submitted.
61. As a contest grader, I want the 32 public cases to match on status and on ordered steps before the 518-case run, so that a full file is not produced from a broken engine.
62. As a contest grader, I want JSON key order and whitespace ignored, and array order preserved, so that scoring matches the contract.
63. As a later engineer, I want three custom evaluation cases, so that the holes in the public sample are tested: one explicit non-deletion, one tombstone that still exposes PII, and one sync or restore that can recreate deleted data.
64. As a later engineer, I want those custom cases written in the evaluation report, so that they are not injected into the 518-case request file.
65. As a later engineer, I want a usage report for the run that produced the output file, so that model, call count, tokens, and estimated cost are recorded without secrets.
66. As a later engineer, I want the runnable solution, prompts, configuration, and evaluation reports packaged without the dataset or secrets, so that the submission archive is valid.
67. As a privacy auditor, I want a decoy that is linked only to another person left out, so that global activity does not contaminate the case.
68. As a privacy auditor, I want policy, not the person's wish to keep a deletable record, to decide the treatment, so that a request to keep a marketing profile does not override a delete rule.
69. As a privacy auditor, I want an active data flow treated as a risk rather than as a deletion-rules category, so that `DATA_FLOW` is disabled rather than forced into delete, redact, anonymize, or retain.
70. As a privacy auditor, I want a blocked backup retained and a restorable backup blocked, so that rule 14 is applied only when restore access can be blocked.

## Implementation Decisions

- The contract wins over this spec. This spec records only the choices the contract leaves open.
- Status and steps come from a deterministic policy engine. A model extracts facts only. Prompts must not ask for a status or an operation.
- The policy engine consumes a closed case state: a deletion-request flag, subject identifiers, records tagged with a deletion-rules category, and active-flow or restore-risk rows. Free-text findings cannot change the verdict.
- Known deletion and non-deletion wording is a rule. Unmatched wording is a deletion request only when a model returns yes. Otherwise it is `NOT_APPLICABLE`.
- Subject resolution uses the current identity snapshot and the identity audit log. The request email may be historical.
- A resource is relevant only through a grounded link. One cross-reference hop counts. A second hop does not. A deletion-worker timestamp is not a link. The file-local account-number encoding is used only when that snapshot's paired rows agree and no account is already linked.
- Unlinked resources are omitted. `analytics_901` and `account_4857` stay out until a grounded link is found.
- Eligibility uses the manifest capture time. A nested timestamp inside a later file does not make the file eligible. Equal to `audit_at` is eligible.
- Two tables in one SQL file are two copies. An older non-compliant copy is not dropped because a newer file proves a different copy.
- A printed category is authoritative. A resource prefix selects the system only. A missing printed category stops the run.
- Finding operation follows the required action. `DELETE` and still present becomes a remaining-record finding. `REDACT` or `ANONYMIZE` with direct identifiers still present becomes an exposed-PII finding. A compliant retain is not a finding. An enabled copy process is an active data flow. A restorable backup is a restore risk.
- An account tombstone is a redaction. The permitted identifier stays. Name, email, phone, and email hash are removed. There is no tombstone operation.
- A present security audit with no `retention_until` is within the retention period. An explicit `retention_until` before `audit_at` stops the run. A missing legal-hold flag stops the run. No matching rule stops the run. Do not invent a `DELETE`.
- Remediation repeats the findings only, in operation-table order: disable data flows, block restores, then delete, redact, and anonymize.
- Incomplete verification covers the required end state of every relevant record and risk, including ones already compliant. Those future steps use an empty evidence id.
- Complete output is verification only. Each of those steps cites proof.
- Citation prefers a file. Among proving files, the latest capture time wins, then the lowest file id. An activity id or audit id is used only when no eligible file proves the step. Omission from the relevant snapshot may be the cited proof of absence.
- Evidence is parsed once into a local SQLite cache and then queried per case. PDF text is extracted first. Vision is only for screenshots and PDF pages with no usable text.
- The primary model id comes from the environment, must start with `grok-4`, and defaults to `grok-4.7`. `grok-build-0.1` is not in that family. The fallback list comes from the environment, is empty by default, and runs only when the primary call fails. Fallbacks extract facts only. The cache key and the usage report record the model that answered.
- The step object has exactly these fields, in this role: step number, phase, system, resource, operation, state, evidence id. JSON key order and whitespace are not significant. Array order is.

```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_01"
}
```

- Modules, by role, not by path: a request classifier, an identity resolver, an evidence index, a policy engine, a step emitter, and a terminal runner. The runner is the only public seam.
- The sample command scores the public cases and writes a build prediction file. The full command writes the root output file only when every case decides. Either failure mode exits non-zero and does not write that output file.
- Environment names are `DELETION_AUDIT_MODEL` and `DELETION_AUDIT_FALLBACK_MODELS`. The API key stays in the environment and is never logged.

## Testing Decisions

- A good test checks external behavior only: `deletion_status`, and the ordered steps by phase, operation, state, system, resource, and evidence id. It does not assert private function structure, cache table names, or prompt text.
- The module under test is the terminal runner as a whole. Do not add acceptance seams inside the classifier, the identity resolver, the evidence index, or the policy engine.
- Prior art is the existing sample scorer: it reads the public request file and the public answer file, writes predictions, and compares status and step tuples. That command is the regression gate. The 518-case run does not start until all 32 public rows match.
- The three custom cases are additional external cases recorded in the evaluation report. They cover a non-deletion, an exposed tombstone, and a recreation path. They are not inserted into the evaluation request file.
- JSON key order and whitespace must not fail a test. Array order must.
- A blocked case is a failure of the run, not a passing `NOT_APPLICABLE` or a guessed `COMPLETE`.

## Out of Scope

- Organizer-only truth, hidden answers, and generator internals.
- Using `reported_status` or an activity result as proof of state.
- Evidence captured after `audit_at`.
- A model choosing status or writing steps.
- A hardcoded Gemini or Groq client. A fallback is allowed only as an environment list used when the primary call fails.
- Second-hop links, time-window attribution, and nearest-activity attribution.
- Guessing `analytics_901` or `account_4857` without a grounded link.
- Inventing a phase, operation, or state.
- Inventing a tombstone operation.
- Writing a partial output file, or marking a missing fact as `NOT_APPLICABLE`.
- Injecting custom cases into the 518-case request file.
- Deleting a record that policy says to retain, redact, anonymize, or keep as a tombstone.
- Reopening the confirmed design except where a public sample proves a grounded link that this spec currently omits.

## Further Notes

- Accepted decisions live in the architecture decision records: the policy engine owns status and steps; inspecting a deletion is still a deletion request; cite the latest proving file; fail closed rather than guess; a resource needs a grounded link.
- The current sample scorer is behind this spec. Several public cases still block because a linked record has no printed category, and three public cases disagree on status. That is unfinished implementation, not a change to the decisions above.
- `analytics_901` and `account_4857` remain omitted on purpose. A later grounded link may add them. A time window may not.
- The contest grader ignores JSON key order and whitespace and preserves array order. Scoring includes status, identity resolution, discovered records and risks, cited evidence, policy decisions, and step sequence.
