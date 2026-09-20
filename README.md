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


## Run

### Run Tests
```powershell
pytest
```

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
