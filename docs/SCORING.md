# Reproducible scoring

Every new match saves both the current analysis snapshot and an append-only `ScoreRun`. Repeating matching adds a run rather than overwriting the earlier calculation. Run history belongs to the same recruiter as its candidate and job.

## What is saved

- Candidate skills, experience, education and profile revision.
- Job requirements, base weights and job revision.
- Rubric version, effective normalized weights, ratios, canonical matched/missing skills and the local score.
- Provider/model, prompt version, actual AI score, requested AI weight, applied weight, rationale and safe fallback diagnostics.
- Final score, calculation timestamp, snapshot schema version and scoring implementation fingerprint.
- SHA-256 of canonical JSON, excluding the checksum itself. Integer-valued floats and negative zero are normalized so PostgreSQL JSONB round-trips do not create false mismatches.

Names, emails, phone numbers and raw resume text are excluded. Education and skills are still applicant information; access and deletion boundaries apply to snapshots too.

## Calculation example

With every criterion active, 50% skill coverage, full experience and full education gives:

```text
local = 50 * 0.5 + 100 * 0.3 + 100 * 0.2 = 75
AI = 80; applied AI weight = 0.25
final = round(75 * 0.75 + 80 * 0.25, 2) = 76.25
```

A valid AI score of zero remains zero. If the provider fails or AI scoring is disabled, the applied AI weight is zero and the result is entirely local. Requested and applied weights are saved separately. Missing criteria are excluded and active local weights are renormalized. No usable job criteria means an insufficient-requirements result, excluded from rankings.

## Use in the application

Open a candidate, select a job and run matching. Each result has a **Reproducible score** section:

1. Inspect the local/AI values, applied weight and saved revisions.
2. Select **Verify saved score**. The server verifies the fingerprint, recomputes the local total from saved component ratios/weights and replays the final blend.
3. Select **Download score snapshot** to export the exact saved evidence and arithmetic.
4. Select **Show score history** to compare earlier runs and verify them individually.

Verification makes **zero provider requests**. Editing a profile/job or changing server weights cannot change historical arithmetic. A stale analysis may still reproduce correctly: that proves what was previously calculated, not that it is current. The analysis endpoint also returns `is_stale`.

## API

All routes require authentication and recruiter ownership. Other recruiters receive 404 for inaccessible IDs.

| Route | Result |
|---|---|
| GET /api/analyses/{id}/ | Current `scoring_snapshot`, alongside existing analysis fields |
| GET /api/analyses/{id}/reproduce/ | Verify snapshot against the current stored analysis total |
| GET /api/score-runs/?analysis={id}&page=1 | Paginated historical snapshots, newest first |
| GET /api/score-runs/{id}/ | One saved run |
| GET /api/score-runs/{id}/reproduce/ | Verify historical arithmetic |

A successful verification returns `verified: true`, `hash_matches`, `rubric_matches`, `score_matches`, `local_score`, `ai_score`, `applied_ai_weight`, `reproduced_score`, `saved_score` and `external_requests: 0`. Invalid/corrupted/unsupported snapshots return `verified: false` with a safe reason. Verification reports a result with HTTP 200; normal 401/404 rules still apply. POST/PATCH/DELETE on score-runs return 405.

Migration `0009_reproducible_scoring` leaves historical analyses without snapshots. Their original AI contribution cannot be reliably inferred, so verification reports `available: false`; rematch to create the first run. No legacy numbers are fabricated or silently replaced.

## Scope and retention

Reproduction verifies **saved arithmetic**. It does not rerun extraction, guarantee an identical future AI generation, prove the evidence is truthful or establish hiring accuracy. A SHA-256 fingerprint detects accidental changes; it is not a digital signature or protection against a database administrator who can rewrite both data and hash.

The application exposes only read-only history and rejects normal model updates to existing runs. Database administrators and direct SQL remain outside that guarantee. History is deleted through cascading deletion when the candidate or job is deleted, including candidate retention purges. Exported JSON copies must be managed separately. Existing database backups also need appropriate retention.
