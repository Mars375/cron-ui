# cron-ui

Self-hostable dashboard for OpenClaw cron jobs.

## V1

- SQLite persistence
- OpenClaw cron collector with graceful fallback
- Dashboard, jobs list, job detail pages
- HTMX-powered refresh action
- Basic health and JSON APIs

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8906
```

Or:

```bash
python app.py
```

## Environment

- `CRON_UI_DB_PATH`, SQLite path, default `./cron-ui.sqlite3`
- `OPENCLAW_CRON_URL`, OpenClaw cron API base URL, default `http://localhost:8905`
- `CRON_UI_PORT`, web port, default `8906`

## Pages

- `/`, dashboard
- `/jobs`, filtered job list
- `/jobs/{job_id}`, job detail and execution history

## API

- `GET /api/stats`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/executions`
- `POST /api/refresh`
- `GET /health`

## Use case

When a cron starts failing, open `/jobs`, click the job, and inspect recent executions plus the failure rate without leaving the machine.

## Project layout

- `app.py`, FastAPI app
- `collector.py`, OpenClaw API client
- `database.py`, SQLite storage
- `ui/templates/`, HTML views
- `ui/static/`, CSS and JS
- `tests/`, pytest coverage
