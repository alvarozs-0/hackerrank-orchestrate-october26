# Cite the latest file that proves the step

A finding or a `COMPLETE` verification cites a `file_id` when any file captured at or before `audit_at` proves the step. An `activity_id` or `audit_id` is used only when no such file exists. If several files prove the same step, cite the latest `captured_at`. If those timestamps tie, cite the lowest `file_id`.

We rejected citing an activity row when a file also proves the step. The 32 samples cite only files. We also rejected citing the earliest file. `case_15` cites the later log, not the earlier screenshot of the same data flow.

Latest-file is a citation tie-break. It does not drop an older non-compliant copy. Every copy that still shows prohibited data at `audit_at` remains a violation.

## Considered options

- Cite the activity row whenever one exists, because the problem statement lists `activity_id` as valid evidence.
- Cite the earliest file, because it is the original source.

The first disagrees with every sample citation. The second would cite a stale screenshot over a later log and mis-state the record at `audit_at`.

## Consequences

Citation is a pure function of the eligible proving files. An omission snapshot may be the cited proof of absence. A file captured after `audit_at` is never eligible. An older snapshot that still shows prohibited data is its own remaining copy, not a candidate to discard.
