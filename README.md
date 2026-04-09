# cron-ui

Self-hostable dashboard for OpenClaw cron jobs.

## V1

- SQLite persistence
- OpenClaw cron collector with graceful fallback
- Dashboard, jobs list, job detail pages
- HTMX-powered refresh action
- Basic health and JSON APIs

## Docker

### Build and run with Docker Compose

```bash
docker compose up -d --build
curl http://localhost:8906/
```

### Build and run manually

```bash
# Build image
docker build -t cron-ui .

# Run container
docker run -d \
  --name cron-ui \
  -p 8906:8906 \
  -v $(pwd)/data:/app/data \
  cron-ui
```

### Environment variables for Docker

```bash
docker run -d \
  --name cron-ui \
  -p 8906:8906 \
  -e CRON_UI_DB_PATH=/app/data/cron-ui.sqlite3 \
  -e OPENCLAW_CRON_URL=http://host.docker.internal:8905 \
  -v $(pwd)/data:/app/data \
  cron-ui
```

## Run

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8906
```

Or:

```bash
python app.py
```

## Quality checks

```bash
python -m pytest -q
./test-docker.sh
```

GitHub Actions runs the same lightweight CI on `push` and `pull_request`: pytest first, then a Docker smoke test. The current veille baseline is validated with `uvicorn 0.44.0` and `pytest 9.0.3`.

The Docker image now prepares the SQLite parent directory at startup, then drops privileges to the bundled `app` user. That avoids fresh bind-mount permission failures with `./data`.

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
