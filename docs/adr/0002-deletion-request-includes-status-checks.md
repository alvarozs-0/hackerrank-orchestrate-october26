# Inspecting a deletion is still a deletion request

A `request_text` authorizes a deletion audit when it asks to delete, erase, or close the account, or to inspect, confirm, or verify that a deletion happened. Language does not matter. `NOT_APPLICABLE` is only for a different action that does not ask for deletion.

We rejected treating inspect-or-confirm wording as non-authorization. `SPEC.md` originally said that, but `case_25`, `case_26`, and `case_28` are `COMPLETE`. A literal reading of "did not request deletion" would mark those `NOT_APPLICABLE` and fail the sample gate.

## Considered options

- Any text that does not say "delete" or "erase" is `NOT_APPLICABLE`.
- Inspect-or-confirm text is a third status, neither a deletion request nor `NOT_APPLICABLE`.

The first fails the samples. The second is not in the output contract.

## Consequences

A mixed text that includes an erasure ask is a deletion request. A marketing opt-out that does not ask for deletion is not. Policy, not a wish to keep a deletable record, decides the treatment. The classifier must not special-case language. Known deletion and non-deletion patterns are decided in code. Unmatched wording is a deletion request only when a model returns yes. A no, or an uncertain answer, is `NOT_APPLICABLE`.
