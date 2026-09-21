<div align="center">

# ResolveIt

### Civic complaints that don't stop at "submitted". They stop when the fix is verified.

AI-powered, closed-loop civic issue resolution platform<br>
Prarambha 2.0 · Agentic AI · PS 1: Smart Civic Issue Resolution Agent

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini_API-4285F4?logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)

</div>

---

## How it works

```
Report  →  Understand  →  Score & Route  →  Assign  →  Fix + Proof  →  Approve  →  Citizen Confirms
```

A citizen reports a pothole, garbage pile or broken streetlight with text, photo, voice note, video and a map pin. ResolveIt classifies it, scores its severity, routes it to the right department, and follows it until the citizen confirms the fix, or disputes it and reopens the case.

## What makes it different

| | |
|---|---|
| **Closed loop** | A complaint is resolved only after officer proof, admin approval and citizen confirmation. |
| **AI proposes, backend decides** | Every AI action goes through a validated command gate before touching the database. |
| **Explainable** | Severity, priority and department come from transparent rules, with the reasons shown. |
| **Human in the loop** | Low-confidence or non-civic reports go to human review instead of being guessed. |
| **Full audit trail** | Every decision and status change is recorded on a timeline. |
| **Multilingual input** | Reports in English, Hindi and Marathi, including voice. |

## Run it locally

Needs Python 3.11+ and Node.js 20+.

```powershell
# Backend (project root)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then set GEMINI_API_KEY and GEMINI_MODEL
uvicorn backend.app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev                   # opens http://localhost:5173
```

Without an API key the app still runs, but new reports go to manual review.

## Demo login

| Role | Sign in |
|---|---|
| Citizen | Any name and contact number |
| Officer | Pick an officer account · passcode `officer123` |
| Admin | Pick the admin account · passcode `officer123` |

Sample Kolhapur complaints load automatically. Restore them anytime with `python -m backend.scripts.reset_demo_db --yes`. Run the tests with `pytest`.

## Tech stack

**Backend:** FastAPI · SQLAlchemy · SQLite · Pydantic  **AI:** Google Gemini  **Frontend:** React · Vite · Tailwind CSS · Leaflet

---

<sub>Prototype notes: departments are simulated with seeded accounts, the demo login is not real authentication, and severity and SLA values are prototype rules. Please use test data only. Uploaded content is sent to the Gemini API for analysis.</sub>