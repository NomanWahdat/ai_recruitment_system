# Verification record

Verified on 2026-10-26 using the isolated project virtual environment. Machine-readable details: [verification.json](verification.json).

| Check | Observed result |
|---|---|
| Fresh backend installation | Passed; pinned requirements plus resolved constraints |
| Dependency consistency | pip check passed |
| PostgreSQL tests | 79 passed, zero skipped, including concurrent claim/enqueue |
| SQLite tests | 77 passed; two PostgreSQL concurrency cases intentionally skipped |
| Backend statement coverage | 85.16% |
| Python style/static checks | Ruff check and format check passed |
| Frontend checks | ESLint with zero warnings, TypeScript and production build passed |
| Migration consistency | No changes detected |
| Production Django checks | No issues with required secret/database/host configuration |
| Real browser | Sign-in, job creation, bulk upload, worker extraction/failure, correction, matching, human shortlisting, local fallback and mobile navigation passed |
| Running frontend/API | HTTP 200 / 200 |
| Anonymous candidate access | HTTP 401 |
| Screenshots | Eleven real captures with synthetic data |

Coverage is for apps.recruitment statements, excluding migrations, tests and Django admin. Branch and frontend coverage are not claimed. [Full coverage data](coverage.json) records per-file misses, including untested command/provider/error branches.

Browser assertions and capture names are in [verification-browser.json](verification-browser.json); screenshots are in [screenshots/](screenshots/). The browser smoke workflow uses local fallback, not paid AI credentials.

The fresh environment uses Python 3.12.6, Django 5.2.1, spaCy 3.7.5 and requests 2.32.3. A real blank English pipeline and spaCy CLI were checked after correcting the yanked pin and missing Click dependency. The backend's English model is optional; no pretrained model was downloaded.

Frontend commands passed on the installed Node 23.3.0 runtime. The supported project/CI recommendation is Node 22.13+ or Node 24; npm emitted engine warnings for the local odd-numbered runtime, without failing the checked commands.

Docker was unavailable, so container execution is unverified. GitHub Actions is configured but has not been run remotely. Live LLM quality, independent human agreement and demographic fairness remain unmeasured. The evaluation is a small developer-authored synthetic regression set.

The base commit in the JSON identifies the upstream snapshot, not a commit containing the local implementation. These checks were collected before publication on improvement/portfolio-hardening; use the repository history to identify the published implementation commit.


## AI follow-up, 2026-10-27

The provider diagnostics and routing fix passed all **89 PostgreSQL tests**, including ten additional AI tests. A targeted SQLite run passed 68 tests. Backend statement coverage is **85.78%** after the added code. Ruff checks/format, frontend ESLint (zero warnings), and TypeScript passed.

The initial authenticated API and browser checks returned truthful missing-key diagnostics. After the user supplied a Groq key, authenticated model discovery exposed an unavailable old model; switching to `openai/gpt-oss-20b` resolved it. All four API operations (parsing, hybrid matching, explanation and questions) returned validated live Groq output using synthetic fixtures. A real browser verified the connection and rendered Groq results in all three AI Tools panels. The production frontend build passed. The key remains in the ignored local environment file.

Schema rejection, HTTP errors, timeouts, connection errors and Groq-to-Gemini fallback were also exercised with mocks. The live Gemini path is unverified because no Gemini key was supplied. See [initial fallback evidence](verification-ai.json), [live API evidence](verification-ai-live.json), [live browser evidence](verification-ai-live-browser.json), [screenshot](screenshots/12-groq-ai-verified.png), and [setup/troubleshooting](AI_CONFIGURATION.md). Connectivity and schema validation do not establish model accuracy. The earlier table records the previous baseline; this follow-up supersedes its PostgreSQL count and coverage.


## Accuracy evaluation and score reproduction, 2026-10-27

The added features passed **110 PostgreSQL tests**, including 21 new snapshot/evaluation tests, with **86.25% backend statement coverage**. Migration 0009 applied successfully and migration consistency passed. Ruff checks/format, frontend ESLint (zero warnings), TypeScript and the final production build passed.

The focused browser check verified split filters, seven measured challenge failures, evaluation JSON export, two real Groq-backed synthetic matches, append-only score history, snapshot JSON export and saved-score verification with zero provider requests. Both exports matched their server-side records. See [browser evidence](verification-scoring-evaluation-browser.json), [evaluation screen](screenshots/13-accuracy-evaluation.png), [score audit screen](screenshots/14-reproducible-scoring.png) and [machine-readable feature verification](verification-scoring-evaluation.json).

The default offline benchmark processed 24 developer-authored synthetic examples with zero provider calls. Overall skill F1 was 0.8571 and experience MAE 0.2708 years; challenge F1 was 0.6977. The original regression split remained at F1 1.0. These are measured corpus results, not independently established hiring accuracy.

A separate [live evaluation smoke report](evaluation-live-smoke.json) contains two synthetic examples and four validated Groq scores. That verifies the optional live evaluation path; its tiny sample is not a quality benchmark. No independent dataset, independent human agreement, demographic fairness or real hiring outcomes are claimed. The API/worker/frontend remain running locally with the migrated schema and rebuilt screens.


## Recruiter interface simplification, 2026-10-27

The main navigation is now Home, Jobs and Candidates, with Settings & tools retaining standalone AI, processing controls, cross-job rankings and system testing. Job and candidate workspaces group the existing features around the hiring flow. A readable HTML evaluation summary is the main report download; complete JSON and metrics remain in an expandable technical section. No scoring, ownership, retention or human-decision rules were removed.

Validation: **112 PostgreSQL tests passed**, backend statement coverage **86.45%**, Ruff checks/format, frontend ESLint with zero warnings, TypeScript and the final production build passed. A small owner-scoped application job filter supports the contextual candidate review and has regression tests.

The updated full browser workflow passed with zero JavaScript exceptions. It used a newly registered synthetic account, then removed its resumes/jobs and the empty account. Existing recruiter records were not used or changed. The flow verified custom job priorities, AI skill suggestions, bulk reading/failure, readable duplicate errors, evidence/profile correction, inline and standalone AI tools, human application decisions/history, saved-score verification/history/export, readable HTML and complete JSON reports, technical metrics, processing/replacement controls and mobile navigation. Comparison actions are disabled while an update is active.

See [the latest browser report](verification-browser.json), [feature verification](verification-recruiter-interface.json), [recruiter guide and preservation map](RECRUITER_GUIDE.md), [Settings & tools](screenshots/16-settings-tools.png) and [readable summary](screenshots/17-readable-evaluation-summary.png). No independent recruitment-accuracy claim is added by this interface change.
