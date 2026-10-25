# Token usage

Run: full dataset

The policy engine chooses `deletion_status` and `steps_json`. A model is called only to extract typed facts or to answer yes/no on unmatched request text.

Environment: `DELETION_AUDIT_MODEL` (default `grok-4.7`), `DELETION_AUDIT_FALLBACK_MODELS` (empty by default), `XAI_API_KEY`.

| Model | Calls | Input tokens | Output tokens | Estimated USD |
| --- | --- | --- | --- | --- |
| xai/grok-4.7 | 11 | 39065 | 2049 | 0.1479 |

Overall calls: 11
Overall input tokens: 39065
Overall output tokens: 2049
Average tokens per model call: 3737.6
Estimated total cost at published Grok 4.7 rates: $0.0904
Estimated cost per model call: $0.0082
Average tokens per deletion request: 79.4

The code's internal estimate used $3 / $15 per million tokens. Published Grok 4.7 rates are $2.00 per million input tokens and $6.00 per million output tokens. This report uses the published rates. Eleven screenshot calls were cached in `build/extraction_cache.sqlite`.
