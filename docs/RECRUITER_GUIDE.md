# Recruiter guide

The everyday journey is **create a job -> add resumes -> check details -> compare -> decide**. The technical tools are optional; you do not need to understand JSON, model names or benchmark metrics to review candidates.

## Where to start

- **Home:** start a job, upload resumes, or continue work needing attention.
- **Jobs:** manage each role's requirements and candidate matches in one workspace.
- **Candidates:** search your private pool, check resume information, and manage applications.
- **Settings & tools:** find background processing, standalone AI tools, cross-job comparisons and system testing.

## 1. Create a job

Select Create job. Enter the job title, company and description, then the skills, experience and education you need. Suggest skills from description can help; check the suggestions and select Use these skills if appropriate. Nothing replaces your requirements without that action.

Employment type, salary and custom matching priorities are under Additional job details and matching priorities. Default priorities work without editing this section. Custom priorities must add up to 100%.

After saving, the job opens with Candidate matches and Job requirements views. Edit requirements from the latter. Changing requirements marks old comparisons out of date and schedules refreshed results.

## 2. Add resumes

Use Add resumes inside a job, or Upload resumes from Home/Candidates. Upload one to ten PDF/DOCX files, up to 10 MB each. For a single file, manual name/email are optional under an expandable section.

Reading happens in the background. You can keep working. File-by-file messages explain rejected files, including duplicates. A resume added from a job still joins your private candidate pool; that job is selected when you open a candidate from the contextual list.

Search candidates by name, email or skill. Resume status is visible; experience filters are expandable. Pagination remains available.

## 3. Check candidate details

Open a candidate. Candidate details shows the information read from their resume. Use Check candidate details (or Edit checked details) to correct it and confirm your review.

Download resume gives you the original file. See where these details came from opens source-line evidence and the original extracted text. The retention date is available there too.

If reading failed, the page explains what happened. Replace a resume or try reading it again contains the replacement upload and retry controls. A replacement clears the old review and refreshes comparisons. Processing activity shows progress and explicit retries.

## 4. Compare against a job

Select Job match, choose a job, and select Compare candidate. Find another job lets you search beyond the first listed roles.

The result shows a score out of 100, matching skills, skills to check and whether the result needs updating. It supports your review; it is not a probability of hiring success.

- AI-assisted means a validated provider response contributed to that result.
- Standard matching means the built-in rules were used without AI.
- Source details explains the actual provider/model or why standard matching was used.

Explain this match and Prepare interview questions use the selected candidate and job. Earlier saved explanations/questions remain available. Update an out-of-date comparison before using these tools.

How this score was calculated expands the breakdown. Verify saved score replays the saved arithmetic without an AI request. Show previous comparisons opens history. Full component details and the technical JSON download remain available within this section.

## 5. Record your decision

Select Review & decision. Choose the job and add the candidate to it if there is no application yet. Record a next step and a note explaining your evidence.

The existing stages are displayed as New application, In review, Shortlisted, Interview, Hired and Not selected. The allowed transitions remain enforced. Shortlisting and later steps require checked candidate details and a current comparison. Decision history keeps the previous stages and notes. See all applications for this candidate provides the paginated cross-job view.

## Optional tools

| Feature | Where to find it |
|---|---|
| Job rankings | Job -> Candidate matches |
| Compare across jobs | Settings & tools -> Compare across jobs |
| Job parsing/suggestions | Create/edit job -> Suggest skills from description |
| Standalone parsing, explanation, interview tools | Settings & tools -> AI assistant tools |
| Provider connection test and model diagnostics | AI assistant tools -> Connection settings and diagnostics |
| Processing failures/retries | Settings & tools -> Processing activity |
| Reprocess all candidates or refresh all jobs | Processing activity -> Advanced controls |
| Rubric components, snapshot, verification and history | Candidate -> Job match -> How this score was calculated |
| Candidate evidence and source text | Candidate details -> See where these details came from |
| Resume replacement | Candidate details -> Replace a resume or try reading it again |
| Delete a candidate/job | More options in the candidate/job list |
| Accuracy benchmark and exports | Settings & tools -> System testing |

## Understanding the evaluation downloads

System testing assesses the software on fictional examples, not your applicants. It is primarily useful to technical reviewers. The main Download readable summary action produces an HTML document you can open in a browser. Use the browser's Print / Save as PDF if you need a PDF copy.

Technical benchmark data and metrics keeps the complete JSON download, dataset split filters, metrics, ranking baselines, failure cases and fingerprints. The readable summary and technical data describe the same benchmark. Independent labelled data is still needed to establish real-world accuracy. Normal recruiters can complete hiring reviews without downloading either report.
