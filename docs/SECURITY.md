# Security and privacy

| Threat | Implemented control | Remaining operational work |
|---|---|---|
| Anonymous/other recruiter access | Authentication, scoped queries, same-owner cross-resource checks | HTTPS and perimeter controls |
| Public CV URLs | Authorized, audited downloads; no public media route | Do not expose the volume through a static-server alias |
| Browser credential theft | HttpOnly session, CSRF, expiring opt-in API tokens; no localStorage credential | Deployment CSP/XSS review |
| Brute force/expensive calls | Auth/general/expensive throttles | Shared cache and ingress limits for multiple processes |
| Spoofed/oversized documents | Signature/container, size, archive and batch limits | No malware scanner; isolate parser CPU/memory |
| Duplicate resumes | Owner-scoped SHA-256 uniqueness | Different versions intentionally remain distinct |
| Lost/repeated tasks | Persistent rows, leases, deduplication, idempotent results, retry | Monitor errors and measure load before scaling |
| Prompt injection/hallucination | Untrusted-data prompts, schema validation, deterministic skill evidence, human stage transitions | Arbitrary live-model injection is not claimed solved |
| Secret/personal data logging | Identifier/category metadata; provider error bodies/keys excluded | Restrict logs and infrastructure retention |
| Unsafe deployment defaults | Production key validation, secure cookies, HTTPS and modern static storage | Trusted proxy, real origins, persistent volumes, backups |

## External processing

AI is disabled by default. Optional matching sends structured skills, experience and education fields, excluding names, contacts and raw resumes. Explanation/question tools use structured matching data.

Job parsing sends the supplied description. Education snippets and user-defined strings can themselves contain identifiers; minimization is not automatic anonymization. Assess provider retention, contracts and residency before using real candidate data. Local mode requires no AI credentials.

## Retention

New candidates have an expiry deadline (default 180 days). Preview python manage.py purge_expired; enforce with purge_expired --apply from an administrator schedule.

Candidate/job deletion cascades applications, notes and analyses. Old CV files are deleted after transaction commit on replacement/deletion. Audit events store action/target IDs and stage metadata, not copied resumes or review-note text. Retention cleanup removes events older than one year. Backups need their own policy.

Filesystem writes are not database transactions. Interrupted uploads can leave orphan files: reconcile_storage previews unreferenced files older than 24 hours; --apply is explicit. Coordinate database/media backups and encryption at the infrastructure layer.

## Migration

Unowned legacy data stays quarantined. Preview assign_legacy --owner USERNAME and apply only after verifying ownership and retention. Assignment invalidates prior scores. No automatic assignment or destructive cleanup was performed.


Scoring history follows the same owner checks as current analyses. Snapshots exclude names, contact fields and raw resumes, but skills/education are still applicant information. Candidate/job deletion and retention purges remove related ScoreRun rows; independently downloaded snapshots and backups require their own retention. SHA-256 detects accidental corruption, not malicious database rewrites. History APIs are read-only; database administrators/direct SQL remain privileged.

Bundled evaluation reports contain synthetic data only. Private dataset evaluation requires a separate output path and cannot replace the public report. Offline evaluation disables providers; live custom evaluation requires an explicit acknowledgement after consent/de-identification, and sends structured scoring fields. Free-text education fields must also be checked for identifiers. Use anonymous record IDs, since IDs appear in metrics and ranking outputs.
