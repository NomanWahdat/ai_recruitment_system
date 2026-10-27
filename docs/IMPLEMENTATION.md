# Audit-to-implementation record

The original Django/Next.js architecture was retained. The changes below address verified audit findings, with regression evidence in [test_regressions.py](../apps/recruitment/tests/test_regressions.py).

| Audit problem | Implementation | Evidence |
|---|---|---|
| Anonymous/global recruitment data | Authenticated owner-scoped queries and same-owner service checks | Anonymous denial, two-recruiter isolation, forbidden cross-owner matching |
| Public CVs | Authorized download; no public media route | Download ownership and public-media rejection tests |
| Duplicate/ephemeral processing | Persistent tasks, revision deduplication, PostgreSQL claiming, lease recovery | Upload-once, retry, lease and concurrent worker/enqueue tests |
| False success on unreadable files | Failed task/candidate states; explicit retry/replacement | Real blank-PDF test and browser screenshot |
| Broken email/date extraction | Bounded obfuscation normalization and union of work intervals | Standard/obfuscated emails, gaps, overlaps, Unicode dates, education-only cases |
| Misleading scoring | Per-job weights, active-criterion normalization, no technology bonuses, abstention | Weight tests, score constraint, insufficient-requirements test |
| Fake AI/fallback/source | Enabled/configured providers only; schema validation and real source/model | Zero/nonfinite score, empty-primary fallback, mocked HTTP and local-source tests |
| Stale results | Revision invalidation and queued recomputation | Profile/job edits, obsolete-task and idempotent-match tests |
| Missing human workflow | Applications and reviewer decision history | Stage validation and reviewed-profile gate tests; browser transition |
| Weak auth/privacy | Password validators, CSRF, HttpOnly sessions, expiring opt-in tokens | Weak password, CSRF/cookie and token-expiry tests |
| Incomplete interface | Bulk upload, editing, document replacement, server filters/pagination, mobile navigation | Browser workflow and TypeScript/lint/build |
| Misleading dashboard/status | Aggregate proportions, persisted events and worker heartbeat | Aggregate and worker-lifecycle tests |
| Retention/file lifecycle | Expiry preview/apply, post-commit deletion and storage reconciliation | Retention, replacement/delete and orphan-cleanup tests |
| Incomplete portfolio | API/architecture/design/privacy/demo/evaluation docs and real screenshots | README evidence links and machine-readable reports |
| Unmeasured matching quality | Public synthetic corpus with exact-skill/rubric/TF-IDF/LSA comparisons | Evaluation JSON, dataset hash, explicit limitations |

## Scope boundaries

TF-IDF is lexical retrieval; two-dimensional SVD/LSA supplies an optional latent semantic retrieval experiment using the existing NumPy dependency. Its worse measured ranking is reported rather than promoted into the application. OCR, semantic embeddings, organization roles, an applicant portal, independent human annotation and demographic fairness validation remain extensions/research work.

Live-provider quality, container execution and remote GitHub CI are not claimed verified. Refer to [verification](VERIFICATION.md) for actual commands/results.

Legacy unowned records were preserved and quarantined. The source snapshot is connected to the supplied origin; implementation changes remain on a local review branch until explicitly published.
