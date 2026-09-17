# CareerAI — AI Career Intelligence Platform (Backend)

High-performance, production-grade FastAPI backend powering **CareerAI** ("AI Career & Resume Intelligence Platform").

Integrates **Google Gemini AI** (via the official `google-genai` SDK), deterministic ATS compliance algorithms, offline spaCy NLP, custom JWT authentication, and user-scoped SQLite data persistence.

---

## Key Features

- **Google Gemini AI Service**: Multi-model fallback cascade (`gemini-2.5-flash`, `gemini-2.5-pro`) with structured JSON schema outputs and automatic exponential backoff.
- **Job Description Intelligence**: Deep parsing of requirements, seniority levels, core and nice-to-have skillsets, and key responsibilities.
- **9-Dimensional Resume-JD Matcher**: Depth, breadth, domain relevance, toolchain alignment, and leadership impact analysis.
- **Skill Gap & Exact Sentence Evidence**: Direct citation of resume sentences mapped to JD criteria with remediation suggestions.
- **AI Bullet Rewriter**: 6 rewrite modes (Google XYZ framework, ATS keyword optimization, executive tone, technical depth, concise summary).
- **ATS Simulator**: 5-category evaluation (Keywords, Structure, Readability, JD Alignment, Formatting) with actionable fixes.
- **Dynamic Career Roadmap**: Milestone-based progress tracking and capstone project blueprints.
- **Interview Prep & Live Mock Grading**: Role-tailored questions with 5-dimension STAR-method answer evaluation.
- **Application Tracking & Resume Versioning**: User-scoped CRUD endpoints with SQLite persistence.

---

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **AI Engine**: Google Gemini API (`google-genai` SDK)
- **NLP & Parsing**: spaCy (`en_core_web_sm`), scikit-learn (TF-IDF), `pdfplumber`, `python-docx`
- **Database**: SQLite (`sqlite3`) with automatic schema migration
- **PDF Generation**: ReportLab
- **Auth**: Custom JWT (HMAC-SHA256)

---

## Quickstart

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/suyashbelhekar/CarrerAI-backend.git
cd CarrerAI-backend

python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and insert your Gemini API Key:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=your_jwt_secret_key
HOST=127.0.0.1
PORT=8000
```

### 4. Run Development Server
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
- **API Root**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## API Reference Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/status` | GET | Check backend health & Gemini status |
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Authenticate & acquire JWT |
| `/api/auth/me` | GET | Get current authenticated user |
| `/api/auth/profile` | GET / PUT | Retrieve and update SQLite profile |
| `/api/jd/analyze` | POST | Analyze Job Description |
| `/api/match` | POST | 9D Resume + JD Intelligence Match |
| `/api/skill-gap` | POST | Skill Gap & Sentence Evidence Mapping |
| `/api/rewrite` | POST | AI Bullet Rewriter (XYZ Formula) |
| `/api/tailored-resume`| POST | Generate targeted tailored resume |
| `/api/ats/analyze` | POST | ATS Simulation & Sub-score breakdown |
| `/api/roadmap` | POST / GET | Generate & fetch career roadmap |
| `/api/interview/evaluate` | POST | Evaluate candidate interview answer |
| `/api/applications` | CRUD | Job Application Kanban management |
| `/api/resumes/versions`| CRUD | Resume version control & diff |

---

## License
MIT License.
