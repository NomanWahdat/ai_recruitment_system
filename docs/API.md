# API contracts

Base: http://127.0.0.1:8000/api. Recruitment routes require authentication and owner-scoped access. Another recruiter's ID returns 404. There is no staff bypass in recruiter APIs.

## Authentication

GET /auth/csrf/ returns a CSRF cookie and csrfToken. Retain cookies and send X-CSRFToken on POST /auth/register/ or /auth/login/. Login rotates CSRF; use the csrfToken in its response for later unsafe requests.

Register:
~~~json
{"username":"recruiter","email":"recruiter@example.com","password":"a-strong-unique-password","full_name":"Example Recruiter"}
~~~

Login:
~~~json
{"username":"recruiter","password":"a-strong-unique-password"}
~~~

Browser authentication uses an HttpOnly session, not localStorage. GET /auth/me/ returns the user; POST /auth/logout/ clears the session and revokes tokens.

Non-browser clients may request "issue_token": true at login and use Authorization: Token <token>. Tokens expire after TOKEN_TTL_SECONDS and a new issuance replaces the old token. Login still requires its CSRF handshake.

## Routes

| Route | Methods | Behavior |
|---|---|---|
| /jobs/ | GET, POST | Paginated owned jobs; creation queues matching |
| /jobs/{id}/ | GET, PUT, PATCH, DELETE | Updates invalidate results |
| /jobs/{id}/match/ | POST | Queue only this job; 202 |
| /jobs/{id}/rankings/ | GET | Top ten current matches; stable ordering, no writes |
| /candidates/ | GET, POST multipart | Bounded summaries; upload queues extraction |
| /candidates/{id}/ | GET, PUT, PATCH, DELETE | Evidence, profile correction, file replacement |
| /candidates/{id}/cv/ | GET | Authorized attachment, no-store, audited |
| /candidates/{id}/analyze/ | POST | Queue extraction or refresh matching |
| /candidates/bulk-upload/ | POST multipart | Up to ten repeated files fields |
| /analyses/ and /analyses/{id}/ | GET | Read-only computation/provenance and current scoring snapshot |
| /analyses/{id}/reproduce/ | GET | Verify saved arithmetic and current stored total; zero provider calls |
| /score-runs/ and /score-runs/{id}/ | GET | Owned, paginated immutable scoring history; filter by analysis ID |
| /score-runs/{id}/reproduce/ | GET | Verify historical snapshot without current settings/profile |
| /evaluation/ | GET | Bundled synthetic offline benchmark; 503 if missing or dataset fingerprint differs |
| /applications/ | GET, POST | New applications start at applied |
| /applications/{id}/ | GET, PATCH | Human transitions; decision history included |
| /tasks/ and /tasks/{id}/ | GET | Owned task state/errors |
| /tasks/{id}/retry/ | POST | Retry failed/completed work; active work deduplicated |
| /events/ and /events/{id}/ | GET | Owned audit history |
| /dashboard/ | GET | Aggregates, real events and worker heartbeat |
| /match/ | POST | Match one owned pair |
| /ai/status/ | GET | Redacted provider configuration; no external calls |
| /ai/check/ | POST | Fixed synthetic provider connection test; returns ok and diagnostics |
| /ai/parse-job/ | POST | Structured parsing and truthful source |
| /ai/match-explanation/ | POST | Explain a current analysis |
| /ai/interview-questions/ | POST | Questions for a current analysis |
| /automation/reprocess/ | POST | Queue owned candidate work |
| /automation/matching/ | POST | Queue owned jobs |
| /health/ | GET, public | Database readiness: 200/503 |

## Payloads

Job:
~~~json
{"title":"Backend Engineer","company_name":"Example Lab","description":"Build Python services","required_skills":["Python","Django"],"minimum_experience":2,"education_requirement":"Bachelor of Computer Science","scoring_weights":{"skills":0.5,"experience":0.3,"education":0.2}}
~~~

Custom weights require all three finite values in [0,1], total 1. Empty weights use configured defaults.

Candidate correction:
~~~json
{"skills":["Python","Django","PostgreSQL"],"years_of_experience":"2.0"}
~~~

Correction records review and queues matching. Multipart PATCH cv_file replaces a document and clears prior review.

Match, explanation and questions:
~~~json
{"candidate_id":1,"job_id":1}
~~~

Job parsing:
~~~json
{"job_description":"Python developer with Django experience"}
~~~

Create application:
~~~json
{"candidate":1,"job":1}
~~~

Transition:
~~~json
{"stage":"review","review_note":"Checked source lines and corrected the profile."}
~~~

Transitions: applied -> review/rejected; review -> shortlisted/rejected; shortlisted -> interview/rejected; interview -> hired/rejected; rejected -> review. Hired is terminal. Transitions require a note. Shortlisting/interview/hiring require profile review and current matching. AI cannot change stages.

## Pagination, filtering and errors

Collections return {"count":42,"next":"...","previous":null,"results":[...]}, with 20 items per page and a page parameter.

Jobs: search, title/created_at ordering. Candidates: search, processing_status, min_experience, max_experience, supported ordering. Analyses: job/candidate IDs. Applications: candidate and/or job ID. Candidate summaries omit raw text/evidence; detail includes them.

400 invalid input/file/transition; 401 absent/expired authentication; 403 CSRF; 404 absent/inaccessible; 405 unsupported mutation; 409 duplicate registration; 429 throttling. Duplicate resumes are validation errors. Bulk 202/207 responses report queued records and per-file failures, not completed extraction.

Defaults: anonymous 30/minute, user 300/minute, auth 10/minute, expensive operations 20/minute. Configure shared-cache and ingress limits before multi-process public deployment.


## AI result metadata

AI tools and matching return `response_source` (`groq`, `gemini`, or `local`), `fallback_used`, `fallback_reason` and `provider_attempts` (provider, status, safe message). The source names an external provider only after output schema validation succeeds. `model` accompanies AI-tool results; matching uses `provider_model`. Analysis generation_provenance retains scoring, explanation and question diagnostics independently.

`GET /ai/status/` returns `available`, `verified: false`, `scoring_enabled` and provider configuration entries. Availability is not proof of connectivity. `POST /ai/check/` ignores user content and sends only a fixed synthetic job; it returns `ok`, model and result metadata. A completed test with unavailable providers returns HTTP 200 and `ok: false`; authentication, CSRF and throttling errors retain normal HTTP status codes. Neither endpoint returns keys, raw exception strings or provider response bodies. See [configuration and failure codes](AI_CONFIGURATION.md).


## Evaluation and reproducible scores

A new match includes `scoring_snapshot` and `score_run_id`. The current analysis exposes the snapshot; the owned score-runs collection preserves prior matches. Current/historical verification returns `verified`, fingerprint/component/score comparisons and the reconstructed total with `external_requests: 0`. Current verification also returns `is_stale`; reproducing an old number does not make it a current match. Legacy analyses return `available: false` until rematched. Snapshots and history cannot be supplied through recruiter write APIs. See [saved-score format and guarantees](SCORING.md).

The evaluation route is authenticated. It serves only the complete bundled report, with overall/by-split extraction metrics, ranking comparisons, bootstrap intervals, anonymous failure cases, provenance and limits. It does not run evaluation or accept uploaded/private datasets on a request. Custom and live benchmarks use the explicit [offline/live CLI workflow](EVALUATION.md).
