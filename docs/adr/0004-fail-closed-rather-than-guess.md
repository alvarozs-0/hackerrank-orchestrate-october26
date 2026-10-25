# Fail closed rather than invent a row

If a required extraction fails and no fallback returns the typed fact, the run exits non-zero and does not write `output.csv`. The same stop applies when no deletion rule covers a relevant record, and when a record has no printed category. A guessed status, a partial file, or an invented `DELETE` is not a valid submission.

We rejected best-effort output. The contract requires exactly 518 rows and exact steps. A missing row and a guessed row both fail, and a guessed row hides the bug.

## Considered options

- Skip the case and write the other rows.
- Mark the case `NOT_APPLICABLE` when a fact or a rule is missing.
- Invent `DELETE` when a conditional `RETAIN` rule does not apply.

All three produce a file that looks submittable and is wrong.

## Consequences

The sample gate and the full run use the same rule. An unmatched retention condition does not become a deletion. A present security audit with no `retention_until` is still within retention, because nothing has shown the period ended. An explicit `retention_until` before `audit_at` stops the run. A missing legal-hold flag still stops the run. When a condition is present, code evaluates it. It does not ask a model to fill the gap.
