# AI Recruitment Screening System

A full-stack AI-powered recruitment platform that automates candidate screening, CV analysis, job matching, and interview preparation. Built with Django REST Framework backend and Next.js 15 frontend.

## 🚀 Live Demo

- **Frontend (Vercel)**: *Add your deployed URL*
- **Backend API**: *Add your deployed URL*

## 📸 Screenshots

| Sign In | Dashboard | Candidates |
|---------|-----------|------------|
| ![Sign In](media/demo/signin.png) | ![Dashboard](media/demo/dashboard.png) | ![Candidates](media/demo/candidates.png) |

| Jobs | Rankings | AI Tools |
|------|----------|----------|
| ![Jobs](media/demo/jobs.png) | ![Rankings](media/demo/rankings.png) | ![AI Tools](media/demo/ai_tools.png) |

## ✨ Key Features

### Authentication & Security
- **Token-based Authentication** - Secure login/signup with Django REST Framework tokens
- **Protected Routes** - Frontend route guarding with React Context
- **Session Management** - Automatic token persistence and logout handling

### AI-Powered Recruitment
- **Dual AI Provider Support** - Groq AI (primary) with Gemini AI fallback
- **Smart CV Parsing** - Extract skills, experience, education from PDF/DOCX
- **Candidate-Job Matching** - AI-generated match scores with skill gap analysis
- **Automated Ranking** - Rank candidates per job based on hybrid AI + heuristic scoring
- **Interview Question Generation** - AI-generated tailored interview questions
- **Match Explanations** - Natural language explanations for why candidates match

### Job Management
- Create and manage job postings
- Define required skills, experience levels, and education requirements
- Parse job descriptions with AI to extract structured data

### Candidate Management
- Bulk CV upload (PDF, DOCX)
- Automatic profile extraction (name, email, phone, skills, experience)
- Processing status tracking (pending → processing → completed/failed)
- Individual candidate profiles with full details

### Analysis & Insights
- **Match Scoring** - Weighted algorithm (skills 50%, experience 30%, education 20%)
- **Response Source Tracking** - Know when AI or local heuristics provided results
- **Strengths & Weaknesses** - AI-generated candidate assessment
- **Recommendation Status** - Shortlisted, Consider, or Rejected

### Automation Tools
- **Re-processing Pipeline** - Re-analyze candidates or jobs with one click
- **Matching Engine** - Run AI matching across all candidates and jobs
- **System Status Notifications** - Real-time updates on processing

### Modern UI/UX
- **Global Search** - Search candidates and jobs instantly
- **Responsive Dashboard** - Stats, recent activity, quick actions
- **Toast Notifications** - User feedback for all actions
- **Loading States** - Smooth skeleton loaders

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Django 5.2** | Web framework |
| **Django REST Framework** | API layer |
| **PostgreSQL** | Primary database |
| **spaCy** | NLP for CV text extraction |
| **PyPDF2** | PDF parsing |
| **python-docx** | Word document parsing |
| **Token Authentication** | Secure API access |
| **CORS Headers** | Frontend integration |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Next.js 15** | React framework |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Styling |
| **TanStack Query** | Data fetching & caching |
| **Lucide React** | Icons |
| **Axios** | HTTP client |
| **React Context** | Auth state management |

### AI/ML Integrations
| Provider | Usage |
|----------|-------|
| **Groq AI** | Primary LLM (llama3-8b-8192) for parsing, matching, explanations |
| **Gemini AI** | Fallback LLM for reliability |
| **spaCy NLP** | Named entity recognition, skill extraction |

## 🏗 Architecture Highlights

### Clean Architecture
```
ai_recruitment_system/
├── backend/
│   ├── apps/recruitment/
│   │   ├── auth_views.py      # Token auth (login/register/logout/me)
│   │   ├── models.py          # Job, Candidate, Analysis
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # API endpoints
│   │   └── services/          # Business logic
│   │       ├── ai/            # Groq & Gemini providers
│   │       ├── automation/    # Candidate/Job agents
│   │       ├── matching/      # Scoring & ranking
│   │       └── profile_extractor.py  # CV text extraction
│   └── config/settings/       # Environment-based config
└── frontend/
    ├── app/                   # Next.js App Router
    │   ├── page.tsx           # Dashboard
    │   ├── candidates/        # Candidate pages
    │   ├── jobs/              # Job pages
    │   └── ai-tools/          # AI features
    ├── components/
    │   ├── auth/              # SignIn, SignUp forms
    │   └── layout/            # DashboardLayout, Topbar, Sidebar
    ├── contexts/
    │   └── AuthContext.tsx    # Global auth state
    └── services/              # API service layer
```

### Key Design Patterns
- **Service Layer** - Business logic separated from views
- **Repository Pattern** - Database access abstracted
- **Provider Pattern** - AI providers interchangeable (Groq/Gemini)
- **Graceful Degradation** - Fallback to local heuristics when AI unavailable

## 📊 API Endpoints

### Authentication
```
POST /api/auth/register/     # User registration
POST /api/auth/login/        # User login
POST /api/auth/logout/       # Token invalidation
GET  /api/auth/me/           # Current user info
```

### Core Resources
```
GET/POST /api/jobs/
GET/PUT/DELETE /api/jobs/{id}/
POST /api/jobs/{id}/parse/           # AI job parsing

GET/POST /api/candidates/
GET/PUT/DELETE /api/candidates/{id}/
POST /api/candidates/{id}/analyze/   # AI CV analysis
POST /api/candidates/bulk-upload/    # Multiple CVs

GET/POST /api/analyses/
POST /api/analyses/match/            # AI matching
POST /api/analyses/explain/          # Match explanations
POST /api/analyses/interview-questions/  # Generate questions

GET /api/jobs/{id}/rankings/         # Get ranked candidates
```

## 🧪 Testing

```bash
# Run all tests
python manage.py test apps.recruitment.tests

# Test coverage includes:
# - Model tests (Job, Candidate, Analysis)
# - Authentication API tests
# - REST API endpoint tests
```

**Current Status**: 18 tests passing ✅

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL
- Node.js 18+

### Backend Setup
```bash
# Virtual environment
python -m venv .venv
source .venv/bin/activate  # or .\venv\Scripts\activate on Windows

# Dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Database
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### AI Provider Setup (Optional)
To enable AI features, add to `.env`:
```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
USE_GROQ_AI=true
USE_GEMINI_FALLBACK=true
```

Without AI keys, the system gracefully falls back to local heuristics.

## 🎯 What I Learned

1. **AI Provider Abstraction** - Built a router pattern to switch between Groq and Gemini seamlessly
2. **Graceful Fallbacks** - Ensured the system works even when external AI services are unavailable
3. **Token Authentication** - Implemented secure, stateless auth for SPA architecture
4. **File Processing Pipeline** - Built async processing for CV uploads with status tracking
5. **NLP Integration** - Combined spaCy for entity extraction with LLMs for semantic analysis
6. **Hybrid Scoring** - Balanced AI insights with deterministic heuristics for reliability

## 🔗 Links

- **GitHub**: https://github.com/NomanWahdat/ai_recruitment_system
- **Live Demo**: *Add your deployed URL*
- **My Portfolio**: *Add your portfolio URL*

---

**Built with ❤️ by [Noman Wahdat](https://github.com/NomanWahdat)**
