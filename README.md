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


### API Routes

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning operational status and virtual clock timestamp |
| `GET` | `/api/departments` | List all 10 canonical departments with escalation chains and category codes |
| `GET` | `/api/complaints` | List complaints with optional query filters (`status`, `category`, `department_id`, `limit`) |
| `GET` | `/api/complaints/{id}` | Detailed complaint report including evidence, ai_reasoning, and events |
| `GET` | `/api/complaints/{id}/events` | Chronological append-only audit event log for the specified complaint |

## Tech Stack

## Architecture

## Team
