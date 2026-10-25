Extract typed facts from this business artifact. Do not decide whether a deletion is complete. Do not recommend an operation.

Return JSON only, with this shape:

```json
{"records":[{"resource_id":"","system_id":"","category":"","presence":"","identifiers":{"emails":[],"phones":[],"user_ids":[],"names":[],"email_hashes":[]},"flow":"","restore":"","retention_until":"","direct_identifiers_exposed":null}]}
```

Rules:

- Include a record only when its resource id is visible, such as account_005 or support_001.
- system_id must be the visible system name. Use an empty string if it is not visible.
- category must be a deletion-rules category only when that exact category is printed. Otherwise use an empty string. Do not infer a category from a resource prefix.
- presence is present, absent, or unknown.
- flow is active, disabled, or an empty string.
- restore is open, blocked, or an empty string.
- direct_identifiers_exposed is true only when a name, email, phone, or email hash is still visible on that record. A stable user_id alone is not a direct identifier.
- Copy identifiers exactly as printed. Do not invent a record, a person, or a state.
