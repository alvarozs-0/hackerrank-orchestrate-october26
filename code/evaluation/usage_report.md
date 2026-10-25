# Token usage

Run: full dataset, the command that wrote root `output.csv`.

The policy engine chooses `deletion_status` and `steps_json`. A model is called only to extract typed facts or to answer yes or no on unmatched request text.

| Provider | Model | Calls | Input tokens | Output tokens | Estimated USD |
| --- | --- | --- | --- | --- | --- |
| xai | grok-4.7 | 0 | 0 | 0 | 0.00 |

Overall calls: 0. Overall input tokens: 0. Overall output tokens: 0. Average tokens per request: 0. Estimated total cost: $0. Estimated cost per request: $0.

`DELETION_AUDIT_MODEL` defaults to `grok-4.7`. `DELETION_AUDIT_FALLBACK_MODELS` was empty. No API call succeeded in this run. Eleven screenshots were not sent to vision, so those files did not contribute facts. Text, SQL, JSON, and PDF text were parsed locally.

Cost estimate, if a later run calls Grok 4.7, is $2.00 per million input tokens and $6.00 per million output tokens. This run did not incur that cost.
