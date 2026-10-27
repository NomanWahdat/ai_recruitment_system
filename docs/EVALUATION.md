# Accuracy evaluation

The evaluation feature measures extraction errors and ranking agreement against supplied labels. It provides a repeatable way to find limitations and compare changes. It does not certify suitability for employment decisions.

Open **Settings & tools -> System testing** in the application to inspect the bundled benchmark, switch between splits, compare baselines, review failure cases and download its report. The authenticated `/api/evaluation/` endpoint serves only the complete bundled offline report. A mismatched dataset fingerprint returns 503 instead of silently presenting stale results. Custom/private reports are not published through this endpoint.

## Current dataset and results

[synthetic-v2](../evaluation/dataset.json) contains **24 developer-authored synthetic records**: 12 original regressions and 12 challenge examples. Two explicitly defined jobs have relevance grades from 0 (unsuitable) through 3 (strong evidence). These are not independent recruiter labels, a representative sample, or an independent held-out set. Expected skills describe evidenced capabilities rather than every technology mentioned.

The challenge split includes negated skills, learning intentions, quoted job adverts, unfamiliar technologies, French experience wording, month units, abbreviations, project dates, ongoing work, future dates, missing contact and nontechnical evidence. It intentionally retains failures rather than tuning them away.

| Extraction measure | Regression, 12 | Challenge, 12 | All, 24 |
|---|---:|---:|---:|
| Email exact match | 100% | 100% | 100% |
| Skill micro precision | 100% | 53.57% | 75.00% |
| Skill micro recall | 100% | 100% | 100% |
| Skill micro F1 | 100% | 69.77% | 85.71% |
| Experience MAE, years | 0.00 | 0.54 | 0.27 |

These measured values describe this corpus only. The weaker challenge results expose false positives from negation/quoted requirements and experience failures in unsupported wording. Per-case expected/extracted years and unexpected/missing skills are in [the report](evaluation-results.json). No raw resume text or expected email address is copied into per-case reports.

The earlier [synthetic-v1 report](evaluation-results-v1.json) is retained as historical evidence. It contains the previous optional LSA experiment; its perfect extraction results applied only to the original twelve regression cases.

## Reproduce the offline benchmark

```powershell
.\.venv\Scripts\python.exe tools/evaluate.py --check
```

Offline mode explicitly disables AI even when working keys are configured. It makes no provider requests or database writes. It measures the local dictionary/regex extractor with NLP disabled, then ranks the extracted profiles. PDF/DOCX decoding is covered separately by document tests; this benchmark starts from text.

The report records dataset and service-code SHA-256 fingerprints, Python/scoring versions, selected split, a fixed experience reference date, `k`, bootstrap settings, per-case failures, predictions and ranked IDs. The bundled reference date is 2026-10-27; ongoing experience is evaluated against that date rather than today's moving clock. Regenerate the report after changing data or scoring/extraction code. Runtime timings are measured but will differ across runs and machines.

```powershell
# Preserve the public report when evaluating a subset.
.\.venv\Scripts\python.exe tools/evaluate.py --split challenge --output .runtime/challenge.json
# Optional within-corpus SVD/LSA experiment, limited to 100 records.
.\.venv\Scripts\python.exe tools/evaluate.py --include-lsa --output .runtime/lsa.json
```

`--check` gates the regression split when present (email >= 0.9, experience MAE <= 0.5 years, skill F1 >= 0.8). Otherwise it gates the selected aggregate. These checks are extraction regression guards, not ranking or AI quality certification. Known challenge failures remain visible even when the regression guard passes.

## Evaluate independent labelled data

Prepare consented/de-identified data outside Git, preferably under ignored `.runtime/`. The JSON schema is illustrated below; real studies need many records and actual provenance, not these example labels.

```json
{
  "version": "your-dataset-v1",
  "as_of_date": "2026-10-27",
  "annotation": {"source": "replace with the actual labelling process", "independent": false},
  "jobs": [{"id": "backend", "required_skills": ["Python"], "minimum_experience": 2, "education_requirement": "", "scoring_weights": {}}],
  "records": [{
    "id": "anonymous-001", "split": "test", "category": "example",
    "text": "Skills\nPython\nSummary\n2 years experience",
    "email": "", "years": 2, "skills": ["Python"], "grades": [2],
    "ratings": [[2], [3]]
  }]
}
```

`grades` contains one consensus relevance grade per job, in job-array order. Optional `ratings` contains exactly two annotators' complete grade lists. Use anonymous record IDs: IDs appear in exported reports. Skill labels compare case-insensitively; label canonical skills consistently. Unknown/nonfinite numbers, duplicate IDs, invalid grades/weights/splits and incomplete labels are rejected. Limits: 10 MB, 500 records, 10 jobs and 20,000 characters per resume.

Allowed splits are regression, challenge, train, validation and test. The evaluator does not train a recruitment model; these labels select evaluation subsets and help audit leakage. Separate candidate identities/documents across splits, freeze test labels before changing the implementation, record how annotators were recruited, and resolve disagreements explicitly. The tool detects normalized identical text across splits; it cannot detect near duplicates, undisclosed tuning or verify annotator independence. A `test` label alone does not make the data independently held out. `independence_verified` therefore remains false.

```powershell
.\.venv\Scripts\python.exe tools/evaluate.py --dataset .runtime/labels.json --split test --output .runtime/test-results.json --check
```

Custom datasets require an explicit output path and cannot overwrite the public bundled report. No custom dataset is added to the database or exposed in the UI. Obtain independent labels/data separately; this repository does not manufacture them.

## Optional live AI comparison

```powershell
# Explicit small synthetic connectivity/evaluation smoke test, not a quality study.
.\.venv\Scripts\python.exe tools/evaluate.py --live-ai --limit 2 --output .runtime/live-smoke.json
# Custom data: only after consent and de-identification of the fields sent.
.\.venv\Scripts\python.exe tools/evaluate.py --dataset .runtime/labels.json --split test --live-ai --allow-external-data --output .runtime/live-test.json
```

The default is always offline. Live mode sends only scoring fields (skills, experience, education and job requirements), using the configured providers. It does not send raw resumes, names or email fields. Check education/free-text values for identifying details before external processing. Live mode records provider attempts, successful AI scores and each complete score snapshot; billing cost is **unknown/null**, not invented. Providers can charge for these requests. Missing/failed providers remain labelled as local fallbacks. Use the successful-AI count to distinguish real AI evaluation from fallback-only results.

## Metrics and interpretation

- Email accuracy is exact match, including an expected empty result.
- Skill precision penalizes unexpected skills; recall penalizes missed skills. F1 balances both using pooled micro counts. Undefined values from empty skill sets are reported as zero.
- Experience MAE is the average absolute difference in years; lower is better.
- NDCG@k uses gain `2^grade - 1` and logarithmic rank discount. It rewards placing higher human relevance labels first.
- Recall@k counts grades 2-3 as relevant; no relevant records yields null. MRR is the reciprocal rank of the first relevant record, or zero.
- Rubric ranking is compared with exact extracted skills and TF-IDF over text; live mode adds the hybrid AI ranking. Optional LSA is a within-corpus experiment. Ties use record ID for reproducibility.
- Extraction uncertainty uses 500 resume-level bootstrap resamples, seed 42, with percentile 95% intervals. These are conditional on the supplied corpus and cannot repair sampling bias or tiny datasets.
- If two rating lists are supplied, quadratic weighted Cohen's kappa is reported over the supplied record/job pairs. No variation makes kappa undefined/null. No independent ratings means unmeasured, not perfect agreement.

Education equivalency, OCR, language generalization, demographic fairness, provider costs and real-world hiring outcomes remain unestablished. Saved AI outputs reproduce arithmetic, not identical future model generations. Read [reproducible scoring](SCORING.md) for the audit boundary.

[Evaluation screenshot](screenshots/13-accuracy-evaluation.png). Focused browser reproduction: set `EVIDENCE_ONLY=1` and run `node tools/browser_e2e.cjs` against a running synthetic demo. This check performs two matches and can invoke configured providers.

The main interface provides a plain-language summary and Download readable summary (HTML, printable to PDF). Technical benchmark data and metrics retains the full JSON download and every existing metric/filter. See the [recruiter guide](RECRUITER_GUIDE.md).
