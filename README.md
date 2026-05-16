# AI Recruitment Screening System

A production-ready Django backend foundation for an AI-powered recruitment screening platform. This project is prepared for future CV uploads, AI candidate analysis, candidate ranking, skill extraction, interview question generation, REST APIs, and dashboard integration.

## Features Included in Step 1

- Modular Django project structure
- Dedicated `recruitment` app
- Django REST Framework configuration
- PostgreSQL database configuration
- Environment variable support with `python-decouple`
- CORS support for frontend integration
- Media upload configuration for future CV files
- Static file configuration
- Development and production settings split
- Initial API health check endpoint
- Git-ready project structure

## Tech Stack

- Python 3.12+
- Django 5.2
- Django REST Framework
- PostgreSQL
- django-cors-headers
- python-decouple
- Pillow
- PyPDF2
- python-docx

## Project Structure

```text
ai_recruitment_system/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── __init__.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── __init__.py
├── apps/
│   ├── __init__.py
│   └── recruitment/
│       ├── migrations/
│       │   └── __init__.py
│       ├── services/
│       │   └── __init__.py
│       ├── utils/
│       │   └── __init__.py
│       ├── tests/
│       │   └── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── __init__.py
├── media/
├── static/
└── templates/
```

## Installation

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Create environment file

Copy `.env.example` to `.env` and fill in your values.

```powershell
Copy-Item .env.example .env
```

Example `.env` values:

```env
SECRET_KEY=replace-with-a-secure-secret-key
DEBUG=True

DB_NAME=ai_recruitment_system
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

ALLOWED_HOSTS=localhost,127.0.0.1

OPENAI_API_KEY=
```

## PostgreSQL Setup

Open PostgreSQL shell or pgAdmin and create the database:

```sql
CREATE DATABASE ai_recruitment_system;
```

If needed, create a dedicated user:

```sql
CREATE USER ai_recruitment_user WITH PASSWORD 'strong_password';
ALTER ROLE ai_recruitment_user SET client_encoding TO 'utf8';
ALTER ROLE ai_recruitment_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ai_recruitment_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ai_recruitment_system TO ai_recruitment_user;
```

Then update `.env`:

```env
DB_NAME=ai_recruitment_system
DB_USER=ai_recruitment_user
DB_PASSWORD=strong_password
DB_HOST=localhost
DB_PORT=5432
```

## Database Migrations

```powershell
python manage.py makemigrations
python manage.py migrate
```

## Create Superuser

```powershell
python manage.py createsuperuser
```

## Run Development Server

```powershell
python manage.py runserver
```

The API will be available at:

```text
http://127.0.0.1:8000/api/health/
```

## API Endpoints

### Health Check

```http
GET /api/health/
```

Response:

```json
{
  "status": "ok",
  "message": "AI Recruitment System API Running"
}
```

### Jobs

```http
GET /api/jobs/
POST /api/jobs/
GET /api/jobs/{id}/
PUT /api/jobs/{id}/
DELETE /api/jobs/{id}/
```

Create job request:

```json
{
  "title": "Backend Django Developer",
  "company_name": "Acme Technologies",
  "location": "Remote",
  "employment_type": "full_time",
  "description": "Build REST APIs and backend services using Django.",
  "required_skills": ["Python", "Django", "REST API", "PostgreSQL"],
  "minimum_experience": 3,
  "education_requirement": "Bachelor's degree in Computer Science or equivalent",
  "salary_range": "$60,000 - $90,000"
}
```

### Candidates

```http
GET /api/candidates/
POST /api/candidates/
GET /api/candidates/{id}/
PUT /api/candidates/{id}/
DELETE /api/candidates/{id}/
```

Candidate CV uploads must use `multipart/form-data`.

Allowed file types:

- PDF
- DOCX

Maximum file size:

- 10MB

Create candidate request:

```http
POST /api/candidates/
Content-Type: multipart/form-data
```

Form fields:

```text
full_name=Sarah Khan
email=sarah@example.com
phone_number=+1234567890
cv_file=@sarah_cv.pdf
years_of_experience=4.5
skills=["Python", "Django", "PostgreSQL"]
education=BS Computer Science
linkedin_url=https://www.linkedin.com/in/example
github_url=https://github.com/example
portfolio_url=https://example.com
```

### Bulk Candidate CV Upload

```http
POST /api/candidates/bulk-upload/
Content-Type: multipart/form-data
```

Use the form field name `files` for each uploaded CV.

Example `curl` request:

```bash
curl -X POST http://127.0.0.1:8000/api/candidates/bulk-upload/ \
  -F "files=@john_cv.pdf" \
  -F "files=@sarah_cv.docx"
```

Successful or partially successful response:

```json
{
  "success_count": 1,
  "failed_count": 1,
  "results": [
    {
      "filename": "john_cv.pdf",
      "status": "completed",
      "candidate_id": 1
    },
    {
      "filename": "broken.pdf",
      "status": "failed",
      "candidate_id": 2,
      "error": "Unable to read PDF file."
    }
  ]
}
```

Invalid upload response:

```json
{
  "files": {
    "0": [
      "Only PDF and DOCX files are allowed."
    ]
  }
}
```

### Analyses

```http
GET /api/analyses/
POST /api/analyses/
GET /api/analyses/{id}/
PUT /api/analyses/{id}/
DELETE /api/analyses/{id}/
```

Create analysis request:

```json
{
  "job": 1,
  "candidate": 1,
  "match_score": 87,
  "matched_skills": ["Python", "Django", "REST API"],
  "missing_skills": ["AWS"],
  "strengths": "Strong backend development and API experience.",
  "weaknesses": "Limited cloud platform exposure.",
  "ai_summary": "Candidate is a strong match for the Django backend role.",
  "recommendation_status": "shortlisted",
  "generated_interview_questions": [
    "Explain Django REST Framework serializers.",
    "How do you optimize slow API endpoints?"
  ]
}
```

## Settings Modules

Development uses:

```text
config.settings.development
```

Production uses:

```text
config.settings.production
```

For production deployments, set the environment variable:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.production"
```

## Next Implementation Steps

The next phase should add CV text extraction for uploaded PDF and DOCX files, then store the extracted text on candidate records for AI analysis.

## Demo

Preview screenshots are available in the repository under `media/demo`:

- Sign in page: [media/demo/signin.png](media/demo/signin.png)
- Sign up page: [media/demo/signup.png](media/demo/signup.png)
- Dashboard: [media/demo/dashboard.png](media/demo/dashboard.png)
- Candidates list: [media/demo/candidates.png](media/demo/candidates.png)
- Candidate detail: [media/demo/candidate_detail.png](media/demo/candidate_detail.png)
- Jobs list: [media/demo/jobs.png](media/demo/jobs.png)
- Job detail: [media/demo/job_detail.png](media/demo/job_detail.png)
- Rankings: [media/demo/rankings.png](media/demo/rankings.png)
- AI tools: [media/demo/ai_tools.png](media/demo/ai_tools.png)
- Automation: [media/demo/automation.png](media/demo/automation.png)

You can open these files directly in the project or view them in your code editor to get quick visual references for the main pages.

## Connect & Push to GitHub

If you created a new GitHub repository (for example `https://github.com/NomanWahdat/ai_recruitment_system.git`), run the following locally from the project root to push the code:

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/NomanWahdat/ai_recruitment_system.git
git push -u origin main
```

If you already ran `git init` and committed only the `README.md`, replace `git add .` with `git add README.md` as appropriate.

## Deployment links

After deploying the backend (Railway / Render) and frontend (Vercel), add the live URLs here to make them easy for consumers to find.

Example placement:

- Frontend (Vercel): https://your-app.vercel.app
- Backend (Railway/Render): https://your-backend.up.railway.app

---

