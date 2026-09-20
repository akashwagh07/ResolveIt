# ResolveIt Project Status

AI-powered closed-loop civic issue resolution platform.

## 1. What Is Built (Verified in Code)

- **Core & Config**: `backend/app/config.py` (Pydantic v2 settings, environment overrides), `database.py` (SQLite WAL engine, session management), `clock.py` (virtual clock for SLA and time travel).
- **Data Layer**: `backend/app/models.py` (Department, User, Cluster, Complaint, Evidence, Resolution, Escalation, ComplaintEvent, CommandRejection).
- **State Machine**: `backend/app/state_machine.py` (strict transitions across 11 main states and 6 auxiliary states, terminal state guards).
- **Audit Logging**: `backend/app/events.py` (immutable append-only `complaint_events` log).
- **Command Gate & Executor**: `backend/app/commands.py` & `executor.py` (13 command schemas, role/state/rule validations, rejection tracking via `command_rejections`).
- **LLM Wrapper**: `backend/app/llm.py` (multimodal Gemini calls via official Google GenAI SDK, fallback chain, exponential backoff retries, SHA-256 disk cache, HTTP 429 RESOURCE_EXHAUSTED quota handling, per-call timeout budget `LLM_TOTAL_TIMEOUT_SECONDS`, and 120s monotonic circuit breaker cooldown).
- **Agent 1 & Agent 2**: `backend/app/agents/agent1.py` (multimodal intake, prompt isolation, ontology validation) & `agent2.py` (zero-LLM deterministic decision engine with `ai_unavailable` cooldown fallback).
- **Deterministic Rule Engine**: `backend/app/engines/` (`severity.py` 0-10 scoring, `priority.py` baseline + sensitive bump, `department.py` routing, `sla.py` deadlines).
- **Demo Identity & Auth Layer**: `backend/app/auth.py` & `routers/auth.py` (headers `X-Demo-Role`, `X-Demo-User-Id`, `X-Demo-Passcode`, `X-Citizen-Contact`, `GET /api/auth/whoami`, `GET /api/users`).
- **Action Layer & Endpoints**: `backend/app/actions.py` & `routers/actions.py` (11 actions: accept, confirm_classification, reject_out_of_scope, assign, start_work, approve_resolution, reject_resolution, confirm_resolution, dispute_resolution, resume_work, de_escalate; `GET /api/complaints/{id}/actions`, `POST /api/complaints/{id}/actions/{action}`).
- **Resolution Upload & Verification Hook**: `backend/app/routers/actions.py` & `verification.py` (`POST /api/complaints/{id}/resolution` with 1-4 images, random filenames, `StubVerifier` protocol, automated transition to `ADMIN_VERIFICATION`).
- **Intake Pipeline & API**: `backend/app/pipeline.py` & `routers/complaints.py` (`POST /api/complaints`, `GET /api/complaints` with officer/review filters, extended detail endpoint, `GET /api/evidence/{id}/file`, `GET /api/health` with LLM circuit breaker status).
- **Testing & Scripts**: `backend/tests/` (107 offline unit/integration tests with temp DB isolation and quota mocks), `backend/scripts/reset_demo_db.py`, `backend/scripts/demo_flow.py` (end-to-end HTTP lifecycle flow with 120s timeout, custom flags, dynamic department officer assignment, and step elapsed timing).
- **Frontend Application**: React 18, Vite, Tailwind CSS, React Router v6 (Landing role & passcode picker with `whoami` validation, Role-guarded routing `/officer`, `/admin`, `/citizen`; Officer work queue with SLA overdue badges; ActionPanel with accessible modals; ResolutionForm with before photo reference; BeforeAfter visual comparison; VerificationCard with human decision disclaimer and 3-step tracker; Admin queues with "Needs review" and "Waiting on admin" chips; Leaflet Map, Report form with PCM voice recorder).

## 2. How to Run

### Backend
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.app.main:app --reload --port 8000
pytest
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

### Demo Script & Reset
```powershell
python -m backend.scripts.reset_demo_db --yes
python -m backend.scripts.demo_flow --base http://127.0.0.1:8000
```

## 3. Key Design Decisions

- **Command Pattern Architecture**: Agents and actions only propose commands (`Command`); the backend command gate validates schema, state, and permissions before applying mutations.
- **Deterministic Critical Path**: Severity score, priority tier, department routing, SLA deadlines, and state transitions are purely deterministic Python code—never LLM opinion.
- **Confidence Gating**: Confidence >= 0.85 auto-progresses; 0.60 to 0.84 proceeds with `needs_review=True`; < 0.60 routes to `HUMAN_REVIEW`.
- **Security & Integrity**: Untrusted citizen inputs wrapped in delimiters; random filenames generated on upload; directory traversal blocked on evidence retrieval; passcodes sanitized and verified via constant-time comparison.
- **Offline Reliability**: Deterministic on-disk LLM response caching and virtual clock enable full offline development, repeatable testing, and simulated SLA fast-forwarding.

## 4. Known Limitations

- Demo-grade identity via request headers; full JWT session management not yet implemented.
- No database migrations; schema changes require database reset.
- Open-Meteo weather integration not yet wired into the active pipeline.
- Video processing validates format and metadata but does not yet extract visual keyframes.

## 5. Next Steps (Not Built Yet)

1. Agent 3 verification: multimodal before/after visual comparison with Gemini vision.
2. Deterministic scheduler with demo virtual clock fast-forward and SLA auto-escalation.
3. Dynamic priority engine (rain forecast, GIS proximity to schools/hospitals, duplicate count).
4. Duplicate and cross-type root-cause clustering engine.
5. Escalation dossier generator.
6. Benchmark evaluation set and production deployment.
