# AI responses and local fallback

The app supports Groq first and Gemini second. A local result is never evidence that an external AI model ran. The actual validated provider and model accompany every generated response.

## Why this checkout was always local

At the initial check on 2026-10-27, the local settings had no Groq or Gemini key. Both providers and hybrid scoring were disabled. Earlier demo server/worker processes also started with explicit false environment overrides. Changing a file alone cannot change settings in already-running processes. The Gemini default was also the obsolete `gemini-pro` identifier. No live provider call was possible in that state.

The fix adds authenticated configuration diagnostics, a synthetic connection test, actionable fallback reasons, JSON object mode for Groq, an adjustable bounded timeout, a current configurable Gemini default, and visible provenance. The local development flags have been enabled at the user's request; a valid API key is still required. Credentials are never created, committed, returned by diagnostics, or put in the browser.

After the user saved a Groq key, the old `llama-3.3-70b-versatile` identifier returned HTTP 404. Authenticated Groq model discovery returned `openai/gpt-oss-20b`; that model passed a synthetic connection test. The API and worker were restarted. Live job parsing, hybrid matching, explanations and interview questions all returned validated Groq output. The browser verified the connection and all three AI Tools panels. See [live API evidence](verification-ai-live.json), [live browser evidence](verification-ai-live-browser.json), and the [real screenshot](screenshots/12-groq-ai-verified.png). These checks establish connectivity and schema handling, not hiring accuracy.

## Configure one provider

Edit the existing root `.env`. Preserve its secret and database configuration. Obtain a key from your own provider account; never paste it into chat or commit it.

Groq:

```dotenv
USE_GROQ_AI=true
GROQ_API_KEY=replace-with-your-real-key
GROQ_MODEL=openai/gpt-oss-20b
```

Or Gemini (works on its own when Groq is unavailable):

```dotenv
USE_GEMINI_FALLBACK=true
GEMINI_API_KEY=replace-with-your-real-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Set `USE_LLM_FOR_SCORING=true` to allow hybrid matching as well as AI tools. With the default `LLM_SCORE_WEIGHT=0.25`, a validated AI score contributes 25% and the local rubric 75%. When scoring is disabled the AI tools can still use providers. CV extraction remains a local PDF/DOCX, dictionary/regex and optional spaCy pipeline; enabling a provider does not change extraction into an LLM parser.

`AI_REQUEST_TIMEOUT=30` allows up to 30 seconds per provider (bounded to 1-60). There are at most two provider calls per operation, no hidden retry loop. HTTPS endpoints are required; redirects are not followed with credentials. A provider's model availability, quota, billing, region and permissions depend on the account. An OpenAI key is not used by these Groq/Gemini integrations.

Restart **both** the Django API and `process_tasks` worker after editing settings. Shell/service environment variables take precedence over `.env`; clear any stale `USE_GROQ_AI=false`, `USE_GEMINI_FALLBACK=false` or `USE_LLM_FOR_SCORING=false` overrides in the service launcher.

Verify configuration without an external request:

```powershell
.\.venv\Scripts\python.exe manage.py check_ai
```

Verify actual access with a fixed synthetic job description:

```powershell
.\.venv\Scripts\python.exe manage.py check_ai --live
```

The live command exits with an error if neither provider returns valid output. In the app, open **AI Tools** and select **Test AI connection**. Configured means settings are present; only a successful test verifies an actual provider response. The test does not measure quality and never sends candidate data. Regenerate a job parse, explanation or questions after configuration; historical saved local results do not automatically turn into AI responses. Rematch a candidate/job to refresh its scoring provenance.

## What local results mean

- Job parsing: `services/ai/prompts/job_parser.py` uses the skill dictionary, role/level keywords and a description excerpt.
- Resume extraction: `services/profile_extractor.py` and its helpers parse text, skill aliases, dates and education. Source evidence and corrections remain important.
- Matching: `services/matching/scorer.py` calculates explicit skill, experience and education coverage. Default weights are 0.5/0.3/0.2, renormalized over active requirements. For example, 50% skill coverage and full experience/education coverage gives 75/100 with all three default criteria active. A job with no usable requirements abstains from ranking.
- Explanations: the fallback lists canonical matched skills and missing skill evidence, then asks for human review.
- Questions: local templates refer to matched/missing skills and include a fixed behavioral question.

These outputs can be reproducible and correct against their rules while missing real qualifications. Dictionary coverage is limited, experience/education estimates are approximate, there is no OCR, and a score is not a probability of hiring success. AI output can also be wrong. Human evidence review remains required.

## Diagnostics and failure behavior

`GET /api/ai/status/` is authenticated and checks configuration only. `POST /api/ai/check/` is authenticated, throttled and sends a fixed synthetic request. Normal AI endpoints and matching return `response_source`, `fallback_used`, `fallback_reason` and redacted `provider_attempts`. Scoring provenance is retained with analyses; explanation/question provenance is retained separately.

Missing keys, disabled providers, blank settings and insecure endpoints are detected before a request. Provider failures distinguish authentication, permissions, missing model/endpoint, rate limit/quota, server failure, timeout, connection failure and invalid response schema. HTTP 429 can mean rate limit or exhausted quota; diagnostics do not guess which. Raw exception strings and provider bodies are not shown or logged. A failed primary may still produce a validated Gemini result; only failure of all eligible providers produces local output.

Official references checked 2026-10-27: [Groq model](https://console.groq.com/docs/model/openai/gpt-oss-20b), [Groq JSON mode](https://console.groq.com/docs/structured-outputs), [Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [Gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations). Model identifiers remain configurable. No live provider success is claimed without credentials and a recorded successful test.


Focused browser reproduction (the live variant makes provider requests with synthetic fixtures):

```powershell
$env:AI_ONLY='1'
$env:LIVE_AI='1'
node tools/browser_e2e.cjs
```

The full browser workflow uses an isolated synthetic account and follows the configured provider settings; it can make live scoring/assistant calls when AI is enabled. CI disables providers for offline regression checks. Focused AI checks require LIVE_AI=1 when a provider is configured. Do not overwrite a working private key to simulate failure. Initial offline evidence is preserved separately from the live browser report.
