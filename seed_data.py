"""Seed the database with sample jobs and candidates, then trigger matching via API."""
import os, sys, django

# Bootstrap Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

import requests, json
from decimal import Decimal
from apps.recruitment.models import Job, Candidate

BASE = "http://localhost:8000/api"

# ── Jobs ──────────────────────────────────────────────
jobs_data = [
    {
        "title": "Senior Python Backend Developer",
        "company_name": "TechNova Inc.",
        "location": "Remote",
        "employment_type": "full_time",
        "description": (
            "We are looking for a Senior Python Backend Developer to design and build scalable "
            "APIs and microservices. You will work with Django, PostgreSQL, Redis, and Docker in "
            "a cloud-native environment on AWS. Experience with CI/CD pipelines, unit testing, "
            "and agile workflows is required. The ideal candidate has 5+ years of backend experience."
        ),
        "required_skills": [
            "Python", "Django", "PostgreSQL", "Redis", "Docker",
            "AWS", "REST API", "CI/CD", "Unit Testing", "Microservices"
        ],
        "minimum_experience": 5,
        "education_requirement": "Bachelor's in Computer Science or related field",
        "salary_range": "$120,000 - $160,000",
    },
    {
        "title": "Frontend React Developer",
        "company_name": "PixelCraft Studios",
        "location": "New York, NY",
        "employment_type": "full_time",
        "description": (
            "PixelCraft Studios is hiring a Frontend React Developer to build beautiful, "
            "responsive web applications. You'll work with React, TypeScript, Next.js, and "
            "TailwindCSS. Experience with state management (Redux/Zustand), REST/GraphQL APIs, "
            "and modern testing frameworks is a plus. 3+ years of frontend experience required."
        ),
        "required_skills": [
            "React", "TypeScript", "Next.js", "TailwindCSS", "JavaScript",
            "Redux", "GraphQL", "HTML/CSS", "Git", "Responsive Design"
        ],
        "minimum_experience": 3,
        "education_requirement": "Bachelor's degree preferred",
        "salary_range": "$90,000 - $130,000",
    },
    {
        "title": "Machine Learning Engineer",
        "company_name": "DataMind AI",
        "location": "San Francisco, CA",
        "employment_type": "full_time",
        "description": (
            "DataMind AI seeks a Machine Learning Engineer to develop and deploy production ML "
            "models. You will work with Python, TensorFlow, PyTorch, and cloud ML platforms. "
            "Strong skills in NLP, computer vision, or recommendation systems are valued. "
            "Experience with MLOps, Docker, and Kubernetes for model serving is essential. 4+ years."
        ),
        "required_skills": [
            "Python", "TensorFlow", "PyTorch", "Machine Learning", "NLP",
            "Docker", "Kubernetes", "AWS", "Data Science", "MLOps"
        ],
        "minimum_experience": 4,
        "education_requirement": "Master's or PhD in CS, AI, or related field",
        "salary_range": "$140,000 - $190,000",
    },
    {
        "title": "Full Stack JavaScript Developer",
        "company_name": "WebFlow Solutions",
        "location": "Austin, TX",
        "employment_type": "contract",
        "description": (
            "WebFlow Solutions needs a Full Stack JavaScript Developer for a 12-month contract. "
            "You will build end-to-end features using Node.js, Express, React, and MongoDB. "
            "Familiarity with TypeScript, Docker, and cloud deployment (AWS/GCP) is expected. "
            "2+ years of full stack experience required."
        ),
        "required_skills": [
            "JavaScript", "Node.js", "Express", "React", "MongoDB",
            "TypeScript", "Docker", "AWS", "Git", "REST API"
        ],
        "minimum_experience": 2,
        "education_requirement": "Bachelor's degree or equivalent experience",
        "salary_range": "$80,000 - $110,000",
    },
]

# ── Candidates ────────────────────────────────────────
candidates_data = [
    {
        "full_name": "Sarah Chen",
        "email": "sarah.chen@example.com",
        "phone_number": "+1-555-0101",
        "skills": [
            "Python", "Django", "Flask", "PostgreSQL", "Redis",
            "Docker", "AWS", "REST API", "CI/CD", "Microservices",
            "Unit Testing", "Git"
        ],
        "years_of_experience": Decimal("7.0"),
        "education": "M.S. Computer Science, Stanford University",
    },
    {
        "full_name": "James Rodriguez",
        "email": "james.rod@example.com",
        "phone_number": "+1-555-0102",
        "skills": [
            "React", "TypeScript", "Next.js", "TailwindCSS", "JavaScript",
            "Redux", "GraphQL", "HTML/CSS", "Git", "Responsive Design",
            "Figma", "Jest"
        ],
        "years_of_experience": Decimal("4.0"),
        "education": "B.S. Software Engineering, MIT",
    },
    {
        "full_name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone_number": "+1-555-0103",
        "skills": [
            "Python", "TensorFlow", "PyTorch", "Machine Learning", "NLP",
            "Docker", "Kubernetes", "AWS", "Data Science", "MLOps",
            "Pandas", "Scikit-learn"
        ],
        "years_of_experience": Decimal("5.0"),
        "education": "Ph.D. Artificial Intelligence, Carnegie Mellon University",
    },
    {
        "full_name": "Alex Thompson",
        "email": "alex.t@example.com",
        "phone_number": "+1-555-0104",
        "skills": [
            "JavaScript", "Node.js", "Express", "React", "MongoDB",
            "TypeScript", "Docker", "AWS", "Git", "REST API",
            "Python", "PostgreSQL"
        ],
        "years_of_experience": Decimal("3.0"),
        "education": "B.S. Information Technology, University of Texas",
    },
    {
        "full_name": "Maria Gonzalez",
        "email": "maria.g@example.com",
        "phone_number": "+1-555-0105",
        "skills": [
            "Python", "Django", "React", "PostgreSQL", "Docker",
            "AWS", "REST API", "Git", "JavaScript", "Redis"
        ],
        "years_of_experience": Decimal("4.0"),
        "education": "B.S. Computer Science, UCLA",
    },
    {
        "full_name": "David Kim",
        "email": "david.kim@example.com",
        "phone_number": "+1-555-0106",
        "skills": [
            "React", "JavaScript", "TypeScript", "Node.js", "Express",
            "MongoDB", "TailwindCSS", "Git", "Docker", "GraphQL"
        ],
        "years_of_experience": Decimal("2.0"),
        "education": "B.A. Web Development, NYU",
    },
    {
        "full_name": "Emily Watson",
        "email": "emily.w@example.com",
        "phone_number": "+1-555-0107",
        "skills": [
            "Python", "Machine Learning", "TensorFlow", "NLP",
            "Data Science", "Pandas", "AWS", "Docker"
        ],
        "years_of_experience": Decimal("2.0"),
        "education": "M.S. Data Science, Columbia University",
    },
    {
        "full_name": "Omar Hassan",
        "email": "omar.h@example.com",
        "phone_number": "+1-555-0108",
        "skills": [
            "Python", "Django", "Flask", "PostgreSQL", "Docker",
            "Kubernetes", "AWS", "CI/CD", "Microservices", "REST API",
            "Redis", "Unit Testing", "Celery"
        ],
        "years_of_experience": Decimal("6.0"),
        "education": "B.S. Computer Engineering, Georgia Tech",
    },
]

print("=" * 60)
print("  SEEDING AI RECRUITMENT SYSTEM")
print("=" * 60)

# Create jobs via API (no file required)
created_jobs = []
print("\n--- Creating Jobs ---")
for jd in jobs_data:
    r = requests.post(f"{BASE}/jobs/", json=jd)
    if r.status_code == 201:
        j = r.json()
        created_jobs.append(j)
        print(f"  [OK] Job #{j['id']}: {j['title']}")
    else:
        print(f"  [FAIL] {jd['title']}: {r.status_code} {r.text[:200]}")

# Create candidates directly via ORM (cv_file is required by serializer but optional in ORM)
created_candidates = []
print("\n--- Creating Candidates ---")
for cd in candidates_data:
    cand = Candidate.objects.create(
        full_name=cd["full_name"],
        email=cd["email"],
        phone_number=cd.get("phone_number", ""),
        skills=cd["skills"],
        years_of_experience=cd["years_of_experience"],
        education=cd.get("education", ""),
        processing_status=Candidate.ProcessingStatus.COMPLETED,
        extraction_success=True,
        analysis_completed=True,
    )
    created_candidates.append(cand)
    print(f"  [OK] Candidate #{cand.id}: {cand.full_name} ({cand.years_of_experience}yr, {len(cand.skills)} skills)")

# Run matching for every candidate-job pair via API (uses Groq hybrid scoring)
print("\n--- Running Matching & Ranking (via Groq AI) ---")
for job in created_jobs:
    print(f"\n  Job: {job['title']}")
    for cand in created_candidates:
        r = requests.post(f"{BASE}/match/", json={
            "candidate_id": cand.id,
            "job_id": job["id"],
        }, timeout=30)
        if r.status_code == 200:
            d = r.json()
            src = d.get("response_source", "unknown")
            print(f"    {cand.full_name:20s} -> score={d.get('match_score'):>6}  src={src}")
        else:
            print(f"    {cand.full_name:20s} -> FAIL {r.status_code} {r.text[:100]}")

# Show final rankings
print("\n" + "=" * 60)
print("  FINAL RANKINGS")
print("=" * 60)
for job in created_jobs:
    r = requests.get(f"{BASE}/jobs/{job['id']}/rankings/")
    if r.status_code == 200:
        data = r.json()
        print(f"\n  {job['title']} ({job['company_name']})")
        print(f"  {'─' * 50}")
        for entry in data.get("top_candidates", []):
            cid = entry["candidate_id"]
            name = next((c.full_name for c in created_candidates if c.id == cid), f"#{cid}")
            print(f"    #{entry['ranking_position']:>2}  {name:20s}  score = {entry['match_score']}")

print("\n" + "=" * 60)
print("  SEEDING COMPLETE - Open http://localhost:3000 to view")
print("=" * 60)
