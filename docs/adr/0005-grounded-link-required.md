# A resource needs a grounded link

A resource is relevant only when a file or activity row at or before `audit_at` ties it to the subject's current or historical identifier, `user_id`, or a same-row cross-reference such as `subject_reference` or `source_resource_id`. A deletion-worker timestamp is not a link. If every present account row in a snapshot encodes the user number in the account id, an omitted subject uses that encoding.

We rejected attributing the nearest deletion-worker target. That window also contains other people's accounts. The account event nearest `case_31`'s reported time is not `account_4857`. We will omit `analytics_901` and `account_4857` until a grounded link is found, even though the sample output names them.

## Considered options

- Attribute every deletion-worker target between `requested_at` and `reported_at`.
- Attribute the deletion-worker target closest to `reported_at`.
- Derive every account id from the user number, even when the snapshot does not use that encoding.

The first two pull in another person's account. The third is false in replica tables where the account number and the user number differ.

## Consequences

A wrong link is worse than a sample miss. Decoys stay out. The sample gate will show the misses. Do not "fix" them by time proximity. One cross-reference hop counts. A second hop does not: if A points at B and only C identifies the subject, A is not relevant.
