# Deterministic policy engine decides status and steps

The grader scores `deletion_status` and ordered `steps_json` exactly, including operation, state, system, resource, and evidence id. A model may only extract facts: whether `request_text` is a deletion request, and which identifiers or records appear in unstructured evidence. A deterministic policy engine turns that case state into `deletion_status` and `steps_json`.

We rejected letting the model write steps, which `SPEC.md` originally proposed. Free-form generation drifts on order and citations and cannot be regression-tested against `sample_output.csv`.

## Considered options

- The model writes steps, and code only checks that the JSON schema is valid.
- The model proposes steps, and code repairs order and citations.

Schema checks and repair still hide policy bugs inside the model. A wrong status must be a code bug.

## Consequences

Prompts must not ask for a status or an operation. Extraction returns structured facts, not a verdict: identifiers seen, `system_id`, `resource_id`, a `deletion_rules.csv` category if one is printed, and a state observation such as present, absent, redacted, anonymized, flow enabled, or restore blocked. The policy engine consumes only typed facts: a deletion-request flag, subject identifiers, records tagged with a category, and active-flow or restore-risk rows. Free-text findings cannot change the verdict. If a required extraction fails and no fallback answers, the run stops and does not write a partial `output.csv`. `sample_output.csv` is the regression gate before the 518-case run.
