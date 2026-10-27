# Demonstration

Use portfolio_demo / PortfolioDemo!2026 after python manage.py seed_demo.

1. Create a backend role requiring Python, Django and PostgreSQL.
2. Run python tools/create_demo_files.py.
3. In Candidates, upload both evaluation/fixtures/sample-cv.docx and unreadable.pdf.
4. Watch queued tasks in Automation, with python manage.py process_tasks running.
5. Open Riley's profile. The raw source table contains Postgres; inspect its source-line evidence.
6. Review/correct the skills to canonical Python, Django, PostgreSQL. Saving records review and invalidates previous scores.
7. Select the job, run matching, and inspect score components/skill gaps.
8. Create an application and move applied -> review -> shortlisted with evidence-based notes. Open decision history.
9. Inspect that job's rankings. Without configured providers, explanation/question tools must report local output.
10. The unreadable PDF must show failed extraction and guidance to supply a text-based document. Retry is explicit. Replacing its source clears prior review and queues extraction.
11. Inspect persistent failures/events and sign out to verify private data is inaccessible.

## Browser automation

With frontend, API and worker running:

~~~sh
python tools/create_demo_files.py
node tools/browser_e2e.cjs
~~~

Requires Node 22+ and Edge/Chrome. BROWSER_BIN overrides discovery. The script drives real forms/uploads, checks persistence, and writes [browser verification](verification-browser.json) plus [screenshots](screenshots/).

The test reserves synthetic Riley/blank-PDF fixtures in the demo account. KEEP_E2E_DATA=1 retains a successful run for manual inspection; default cleanup removes its records. Screenshots are authentic workflow captures, not evidence of AI accuracy.


## Demonstrate the new evidence features

1. Open Evaluation and select the challenge split. Explain skill F1 69.77%, experience MAE 0.54 years, and the concrete negation/quoted-job failures. Switch to regression to show why testing only the easy cases gave a misleadingly perfect extraction result.
2. Download the evaluation report. Point to dataset/code fingerprints and the fixed reference date. Explain that independent data/labels must be supplied through the CLI; the bundled corpus is synthetic.
3. Open Kate Example, select Backend Engineer and run matching. Inspect the local score, real provider score and applied weight in Reproducible score.
4. Verify the saved score: the total is reconstructed with zero AI calls. Download the snapshot.
5. Rematch, open score history and verify an older run. Live AI outputs can vary; each original run remains inspectable and reproducible as saved arithmetic.

[Feature browser report](verification-scoring-evaluation-browser.json) records the actual checked flow and downloads. See [evaluation](screenshots/13-accuracy-evaluation.png) and [score history](screenshots/14-reproducible-scoring.png) captures.
