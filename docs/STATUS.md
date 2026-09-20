# ResolveIt Project Status

AI-powered closed-loop civic issue resolution platform.

## 1. Feature Implementation Status

### Built (Verified in Code)
- **Deterministic Rule Engine**: Pure Python implementations for severity scoring (0–10 in `severity.py`), priority calculation with vulnerable zone bumps (`priority.py`), department routing across 10 municipal departments (`department.py`), and SLA deadline calculation (`sla.py`).
- **Command Pattern Gate & Executor**: 13 command schemas (`commands.py`), strict caller permission checks across 7 actors (`Actor`), state validity checks, and atomic execution with rejection logging (`executor.py`).
- **State Machine**: 11 primary states and 6 auxiliary states in `state_machine.py`, strict transition graph, terminal state protections, and immutable audit event logging (`events.py`).
- **LLM Wrapper & Quota Resilience**: Official Google GenAI SDK integration (`llm.py`), fallback chain (`gemini-3.6-flash` -> `gemini-3.5-flash` -> `gemini-3.7-flash`), per-call timeout budget (`LLM_TOTAL_TIMEOUT_SECONDS=25`), SHA-256 disk cache, HTTP 429 quota classification, and 120s circuit breaker cooldown.
- **Agent 1 & Agent 2**: Multimodal intake with prompt isolation and taxonomy validation (`agent1.py`); zero-LLM deterministic decision orchestration with graceful `ai_unavailable` fallback (`agent2.py`).
- **Demo Identity & Auth Layer**: Header-based persona switching (`X-Demo-Role`, `X-Demo-User-Id`, `X-Demo-Passcode`, `X-Citizen-Contact`), constant-time passcode validation (`auth.py`), `GET /api/auth/whoami`, and `GET /api/users`.
- **Action API & Lifecycle Workflow**: 11 permitted actions (`actions.py`), state transition execution (`POST /api/complaints/{id}/actions/{action}`), available action listing (`GET /api/complaints/{id}/actions`).
- **Resolution Evidence & Verification Hook**: Multi-image after-photo upload (`POST /api/complaints/{id}/resolution`), automated transition to `RESOLUTION_SUBMITTED` -> `AI_VERIFICATION` -> `ADMIN_VERIFICATION`.
- **Frontend Web Application**: React 18, Vite, Tailwind CSS, React Router v6. Persona selector on landing page with passcode validation, role-guarded routes (`/officer`, `/admin`, `/citizen`), citizen report intake with audio recording and GPS, interactive Leaflet map, officer task queue with SLA indicators, ActionPanel with accessible modals, side-by-side BeforeAfter comparison, VerificationCard with human-in-the-loop controls.
- **Automated Tests**: 107 unit and integration tests passing offline (`pytest`), isolated temporary SQLite databases, mock LLM backends.
- **Demo & Seed Scripts**: `reset_demo_db.py` for atomic drop/reseed of Kolhapur baseline data, and `demo_flow.py` for end-to-end HTTP lifecycle simulation.

### Partial (Partially Implemented)
- **Resolution Verification**: Protocol hook (`run_verification_hook`) and `StubVerifier` are built and active (`VERIFIER=stub`), recording `recommendation="ADMIN_REVIEW"` with `confidence=0.0` for human administrative sign-off. Automated multimodal AI vision verification comparing before/after photos is designed as an extension point but not yet wired to a live vision model.
- **Video Intake**: Accepts, validates MIME types, and stores video evidence files (`.mp4`, `.mov`, `.webm`) up to 30 MB; visual keyframe extraction for LLM analysis is not yet implemented.
- **Passcode Configuration**: Demo passcode configurable via `OFFICER_PASSCODE` in backend; frontend supports optional hint via `VITE_DEMO_PASSCODE_HINT`. Uses demo header authentication rather than JWT/OAuth2 tokens.

### Not Built (Roadmap)
- **Background Scheduler Daemon**: SLA escalation transitions and auto-closure exist in the state machine and commands, but an automated background daemon (cron/worker) polling overdue complaints in real time is not running.
- **Automated Duplicate & Root-Cause Clustering**: `LINK_CLUSTER` command schema and `Cluster` database model exist, but automated spatial-temporal duplicate grouping algorithms are not wired into the active pipeline.
- **Live Weather Integration**: Open-Meteo weather API integration described in specifications is not wired into the active intake pipeline.
- **Evaluation Benchmark Suite**: Benchmark evaluation dataset (`eval/results.md`) is planned for future model fine-tuning and accuracy evaluation.

---

## 2. How to Run

### Backend
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.app.main:app --reload --port 8000
```
*(On macOS/Linux: `source .venv/bin/activate` and `cp .env.example .env`)*

### Frontend
```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

### Run Offline Test Suite
```powershell
pytest
```

### Reset Demo Database
```powershell
python -m backend.scripts.reset_demo_db --yes
```

### Run Lifecycle Demo Script
```powershell
python -m backend.scripts.demo_flow --base http://127.0.0.1:8000
```

---

## 3. Key Design Principles

1. **Agents Propose, Backend Executes**: AI agents never mutate the database directly. All mutations occur via strict Pydantic command schemas validated by the command gate.
2. **Deterministic Rules for Critical Operations**: Severity scoring, priority tiers, department routing, and SLA deadlines are calculated by deterministic Python code—never LLM opinion.
3. **AI Never Closes a Complaint**: Final resolution closure requires explicit citizen confirmation or administrative verification.
4. **Confidence Gating**: High-confidence classifications (>= 0.85) auto-progress; medium-confidence (0.60–0.84) progress with a review flag; low-confidence (< 0.60) routes to human intake review.
5. **Immutable Audit Trail**: Every status transition, priority change, assignment, and action appends an immutable record to `complaint_events`.

---

## 4. Known Limitations

- **Demo Authentication**: Uses custom request headers (`X-Demo-*`) for judging convenience; production deployment requires standard OAuth2 / JWT.
- **Schema Migrations**: Relies on SQLite metadata creation and reseed scripts rather than Alembic migrations.
- **Storage**: Uploaded media and SQLite database reside on local disk; cloud object storage (S3/GCS) is required for horizontally scaled deployments.
