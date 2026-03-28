# BalanceAI

BalanceAI is an AI-powered student planning app that helps users build a weekly schedule, detect burnout risk, and generate a healthier optimized plan.

## Team Members
- **Freeman Yiu** - Integration / Repo Lead / QA
- **Youcheng Taing** - Scheduler / Optimizer
- **Yen Nguyen** - Frontend / UX (React)
- **Matthew Yeung** - Burnout Detection Engine

## What It Does
Users can enter:
- Classes
- Work shifts
- Assignments and study tasks
- Deadlines
- Personal workload preferences

The app then:
- analyzes burnout risk
- explains why a schedule looks unhealthy
- optimizes task placement around fixed commitments
- compares the original and improved weekly plan

## Why It Is AI-Powered
BalanceAI uses a hybrid AI approach rather than a chatbot-based approach.

It combines:
- rule-based burnout scoring
- heuristic and constraint-based scheduling
- explainable workload insights

This means the system makes intelligent planning decisions and produces recommendations based on schedule structure, deadlines, workload limits, and recovery time.

## Current Architecture

### Frontend
- React
- Vite

### Backend
- FastAPI
- Python

### Core Logic
- Scheduler / optimizer in `src/scheduler/`
- Burnout scoring in `src/burnout/`
- API and integration pipeline in `src/api/` and `src/integration/`

### Optional Legacy Demo
- A Streamlit demo entrypoint still exists in `app.py`, but the main app flow is now React + FastAPI.

## Project Structure
```text
frontend/               React frontend
src/api/                FastAPI server
src/integration/        Shared pipeline and analysis helpers
src/scheduler/          Scheduling and optimization logic
src/burnout/            Burnout scoring and explanation logic
tests/                  Backend pytest suite
docs/                   Contracts and notes
```

## How The App Works
1. The user enters schedule data in the React frontend.
2. The frontend sends a JSON payload to `POST /api/analyze`.
3. The backend builds a baseline plan.
4. The scheduler generates an optimized schedule.
5. The burnout engine scores both the baseline and optimized plans.
6. The frontend displays burnout insights and before-vs-after comparison views.

## API

### Health Check
`GET /api/health`

Returns:
```json
{ "status": "ok" }
```

### Analyze Schedule
`POST /api/analyze`

Example request:
```json
{
  "commitments": [
    { "title": "CS 101", "day": "Mon", "start": 9.0, "end": 10.5 }
  ],
  "tasks": [
    { "title": "Essay Draft", "duration": 2.0, "deadline_day": "Tue" }
  ],
  "sleep_window": { "start": 23.0, "end": 7.0 },
  "preferences": {
    "max_daily_hours": 8.0,
    "preferred_study_start": 7.0,
    "preferred_study_end": 22.0,
    "slot_step": 0.5,
    "buffer_hours": 1.0,
    "weekly_hours_threshold": 50.0,
    "late_night_cutoff": 23.0,
    "max_consecutive_blocks": 3,
    "min_breaks_per_day": 1,
    "deadline_cluster_days": 2
  }
}
```

The response includes:
- `before_plan`
- `after_plan`
- `before_assessment`
- `after_assessment`
- `metadata`

See [docs/scheduler_contract.md](/Users/FreemanYiu/Downloads/HackathonAIWellbeing26/docs/scheduler_contract.md) for the scheduler contract.

## How To Run The Project

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd HackathonAIWellbeing26
```

### 2. Set up the Python backend
Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

Start the FastAPI backend:
```bash
uvicorn src.api.server:app --reload --port 8000
```

The backend will run at:
```text
http://127.0.0.1:8000
```

### 3. Set up the React frontend
In a new terminal:
```bash
cd frontend
npm install
```

Start the frontend:
```bash
npm run dev
```

The frontend will run at a Vite local URL, usually:
```text
http://127.0.0.1:5173
```

### 4. Use the app
- Open the frontend in your browser
- Add commitments and tasks
- Click `Analyze and Optimize`
- View burnout analysis and before-vs-after schedule comparison

## How To Run Tests

From the project root:
```bash
source .venv/bin/activate
pytest -q
```

## Optional Commands

Build the frontend:
```bash
cd frontend
npm run build
```

Run the legacy Streamlit demo:
```bash
source .venv/bin/activate
streamlit run app.py
```

## Notes
- The frontend currently expects the backend at `http://127.0.0.1:8000`.
- If the backend is not running, the frontend cannot analyze schedules.
- Backend tests cover scheduler logic, burnout logic, and API behavior.

## Future Improvements
- Calendar export
- Authentication
- Mobile-friendly packaging
- Smarter personalization
- Calendar integrations

## License
MIT License
