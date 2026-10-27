# Design decisions

1. Preserve Django/Next.js. The audit identified concrete reliability/security defects; a framework replacement was unnecessary.
2. Ownership first. Queries and cross-resource matching/application boundaries enforce recruiter ownership. Legacy null owners remain quarantined.
3. Private files. Authorized downloads replace public media URLs. A shared persistent volume preserves the existing parser architecture; object storage is not claimed.
4. Persistent processing. Atomic enqueue, revision keys, PostgreSQL locks, leases and idempotent upserts replace duplicate threads. This avoids an additional queue service for a small project. External calls can repeat after a crash.
5. Evidence and correction. Extracted text/line references remain read-only. Saving reviewed fields timestamps human review, marks scores stale and queues new matching. Replacing a file clears review.
6. Transparent scoring. Defaults are skills 0.5, experience 0.3, education 0.2; each job can override them. Unspecified criteria do not earn free points. Active criteria are renormalized; absent criteria produce an insufficient-requirements result. Technology bonuses were removed. Education matching remains lexical and approximate.
7. Optional AI. Providers must be enabled/configured. Bounded schema validation rejects empty/malformed responses and tries fallback. Zero is valid. Provider/model/prompt/scoring provenance is retained. Deterministic matched/missing skill evidence cannot be silently changed by an LLM.
8. Human stages. Applications, notes, reviewer identity and decision history are separate from computed analyses. Generic analysis writes are disabled.
9. Honest read paths. Rankings do not write during GET. Dashboard metrics use owner-scoped aggregates and persisted events; heartbeat status replaces invented notifications.
10. Evidence over feature count. The evaluation reports where a simpler baseline wins. OCR, semantic embeddings, team roles and an applicant portal are extensions, not marketing claims.

## Dependency correction

The clean installation exposed spaCy 3.7.6 as a yanked release ([maintainer notice](https://pypi.org/project/spacy/3.7.6/)). The pin uses non-yanked [3.7.5](https://pypi.org/project/spacy/3.7.5/) to preserve the existing 3.7 API without introducing a NumPy/Thinc major-version migration. The isolated-environment tests verify this choice.

A clean-install NLP smoke check also caught spaCy's implicit Click import after newer Typer dependency resolution. Click is pinned explicitly, and both a blank English pipeline and the spaCy CLI were verified in the isolated environment.
