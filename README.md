# ResolveIt

AI-powered closed-loop civic issue resolution platform

## Setup

Run the following commands in Windows PowerShell from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

> **Note on Model Changes**: No migrations are used. After making model changes, delete `resolveit.db` and restart the server so tables are re-created and seeded.

### LLM Configuration
Set your Gemini configuration in `.env`:
- `GEMINI_MODEL=gemini-3.6-flash` (Primary multimodal classification model)
- `GEMINI_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.7-flash` (Fallback chain tried sequentially on failure)
- `GEMINI_API_KEY`: Your Google Gemini API key
- `LLM_TOTAL_TIMEOUT_SECONDS=25`: Total timeout budget per classification across all models & retries
- `LLM_QUOTA_COOLDOWN_SECONDS=120`: Circuit breaker cooldown duration when all models return quota exhaustion (HTTP 429)


## Run

### Run Tests
```powershell
# Run all offline unit and integration tests
pytest

# Run tests including live Gemini API test (requires GEMINI_API_KEY and GEMINI_MODEL)
$env:RUN_LIVE_LLM="1"; pytest; Remove-Item Env:\RUN_LIVE_LLM
```

### Try Agent 1 CLI (Classification & Multimodal Intake)
Run classification on local text or multimodal files:
```powershell
python -m backend.scripts.try_agent1 --text "Dangerous deep pothole on MG Road near the school." --address "MG Road"
```
For more options (`--image`, `--audio`, `--video`, `--lat`, `--lng`, `--no-cache`), see [AGENT1.md](file:///docs/AGENT1.md) or run `python -m backend.scripts.try_agent1 --help`.

### Restore / Reset Demo Database
To drop, recreate schema, and reseed departments, users, and the 6 baseline Kolhapur complaints while the dev server is running (without deleting the database file):
```powershell
# Dry run explanation:
python -m backend.scripts.reset_demo_db

# Execute reset:
python -m backend.scripts.reset_demo_db --yes
```



### Run End-to-End Lifecycle Demo Flow
Run against a running backend server to test the entire closed-loop lifecycle (submit report -> admin assign -> officer start work -> officer resolution upload -> admin approve -> citizen confirm):
```powershell
python -m backend.scripts.demo_flow --base http://127.0.0.1:8000
```
Optional flags:
- `--text`: Custom complaint text (default: `"Huge pothole near the school gate for a week, bikes cannot pass"`)
- `--lat`, `--lng`: Custom coordinates (default: `16.7112`, `74.2405`)
- `--name`: Citizen name (default: `"Test User"`)
- `--contact`: Citizen phone number (default: `"+91 9000000000"`)
*Note: If submission enters `HUMAN_REVIEW` (e.g. AI quota exhaustion or low confidence), the demo script automatically prompts admin confirmation before proceeding with department-matched officer assignment.*

### Start Backend Development Server
Run from the repository root:
```powershell
uvicorn backend.app.main:app --reload --port 8000
```

### Start Frontend Development Server
Ensure the backend is running on port 8000, then run in a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
The frontend will start on [http://localhost:5173](http://localhost:5173) with automatic proxying to the backend API.

> **Browser Permissions Note**: In-browser Geolocation (`navigator.geolocation`) and Microphone access (`navigator.mediaDevices.getUserMedia`) are restricted by modern browser security policies and require a secure origin (`localhost` or `https://`).



### API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning operational status, virtual clock, and LLM circuit breaker status |
| `GET` | `/api/departments` | List all 10 canonical departments with escalation chains and category codes |
| `GET` | `/api/auth/whoami` | Resolve demo identity from headers (`X-Demo-Role`, `X-Demo-User-Id`, `X-Citizen-Contact`) |
| `GET` | `/api/users` | List seeded demo accounts for role switching (`OFFICER` or `ADMIN`) |
| `GET` | `/api/complaints` | List complaints with query filters (`status`, `category`, `department_id`, `assigned_officer_id`, `needs_review`, `citizen_contact`, `limit`) |
| `POST` | `/api/complaints` | Intake citizen complaint with optional media (text, image, audio, video) |
| `GET` | `/api/complaints/{id}` | Detailed complaint with resolutions, before/after evidence URLs, officer & department info |
| `GET` | `/api/complaints/{id}/events` | Chronological append-only audit event log for the specified complaint |
| `GET` | `/api/complaints/{id}/actions` | List actions currently available to the authenticated caller on this complaint |
| `POST` | `/api/complaints/{id}/actions/{action}` | Execute permitted workflow action through the command gate |
| `POST` | `/api/complaints/{id}/resolution` | Officer upload of resolution description and 1-4 after images with verification hook |
| `GET` | `/api/evidence/{id}/file` | Securely serve uploaded complaint and resolution evidence files |

## Tech Stack

## Architecture

## Team
