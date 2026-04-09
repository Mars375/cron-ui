#!/usr/bin/env python3
"""cron-ui, self-hostable dashboard for OpenClaw cron jobs."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from collector import CronCollector
from database import CronDatabase

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = Path(os.getenv("CRON_UI_DB_PATH", BASE_DIR / "cron-ui.sqlite3"))
DEFAULT_COLLECTOR_URL = os.getenv("OPENCLAW_CRON_URL", "http://localhost:8905")
DEFAULT_STARTUP_REFRESH_TIMEOUT = float(os.getenv("CRON_UI_STARTUP_REFRESH_TIMEOUT", "3"))
DEFAULT_HEALTHCHECK_TIMEOUT = float(os.getenv("CRON_UI_HEALTHCHECK_TIMEOUT", "1"))

logger = logging.getLogger(__name__)


def create_app(
    db_path: str | Path = DEFAULT_DB_PATH,
    collector: CronCollector | None = None,
    startup_refresh_timeout: float = DEFAULT_STARTUP_REFRESH_TIMEOUT,
) -> FastAPI:
    database = CronDatabase(db_path)
    collector = collector or CronCollector(DEFAULT_COLLECTOR_URL)
    templates = Jinja2Templates(directory=str(BASE_DIR / "ui" / "templates"))

    app = FastAPI(title="cron-ui", version="0.1.0", description="Dashboard OpenClaw Cron Jobs")
    app.state.database = database
    app.state.collector = collector
    app.state.refresh_task = None
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "ui" / "static")), name="static")

    async def refresh_cache() -> dict[str, int]:
        jobs = await asyncio.to_thread(collector.get_jobs)
        executions = await asyncio.to_thread(collector.get_executions)
        for job in jobs:
            database.store_job(job)
        for execution in executions:
            database.store_execution(execution)
        if database.job_count() == 0:
            database.seed_demo_data()
        return {"jobs": len(jobs), "executions": len(executions)}

    async def background_refresh() -> None:
        try:
            await asyncio.wait_for(refresh_cache(), timeout=startup_refresh_timeout)
        except asyncio.TimeoutError:
            logger.warning("Initial cache refresh timed out after %.1fs", startup_refresh_timeout)
        except Exception as exc:  # pragma: no cover - defensive startup fallback
            logger.warning("Initial cache refresh failed: %s", exc)

    async def collector_status() -> dict[str, Any]:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(collector.health_check),
                timeout=DEFAULT_HEALTHCHECK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "base_url": getattr(collector, "base_url", DEFAULT_COLLECTOR_URL),
                "error": f"health check timed out after {DEFAULT_HEALTHCHECK_TIMEOUT:.1f}s",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    @app.on_event("startup")
    async def startup_event() -> None:
        database.initialize()
        if database.job_count() == 0:
            database.seed_demo_data()
        app.state.refresh_task = asyncio.create_task(background_refresh())

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        refresh_task = getattr(app.state, "refresh_task", None)
        if refresh_task and not refresh_task.done():
            refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await refresh_task
        close = getattr(collector, "close", None)
        if callable(close):
            await asyncio.to_thread(close)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        stats = database.get_stats()
        recent_executions = database.get_recent_executions(limit=8)
        failed_jobs = database.get_failed_jobs(limit=5)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "stats": stats,
                "recent_executions": recent_executions,
                "failed_jobs": failed_jobs,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.get("/jobs", response_class=HTMLResponse)
    async def jobs_page(
        request: Request,
        status: str | None = Query(default=None),
        q: str | None = Query(default=None),
    ) -> HTMLResponse:
        jobs = database.get_all_jobs()
        if status:
            jobs = [job for job in jobs if job["status"] == status]
        if q:
            needle = q.lower().strip()
            jobs = [
                job
                for job in jobs
                if needle in job["name"].lower() or needle in job["job_id"].lower() or needle in job["description"].lower()
            ]
        return templates.TemplateResponse(
            request=request,
            name="jobs.html",
            context={
                "jobs": jobs,
                "status_filter": status or "",
                "query": q or "",
            },
        )

    @app.get("/jobs/{job_id}", response_class=HTMLResponse)
    async def job_detail(request: Request, job_id: str) -> HTMLResponse:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return templates.TemplateResponse(
            request=request,
            name="job_detail.html",
            context={
                "job": job,
                "executions": job.get("recent_executions", []),
            },
        )

    @app.get("/api/stats")
    async def api_stats() -> dict[str, object]:
        return database.get_stats()

    @app.get("/api/jobs")
    async def api_jobs() -> dict[str, object]:
        jobs = database.get_all_jobs()
        return {"jobs": jobs, "count": len(jobs)}

    @app.get("/api/jobs/{job_id}")
    async def api_job(job_id: str) -> dict[str, object]:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.get("/api/executions")
    async def api_executions(limit: int = 50, offset: int = 0) -> dict[str, object]:
        executions = database.get_executions(limit=limit, offset=offset)
        return {"executions": executions, "count": len(executions), "limit": limit, "offset": offset}

    @app.post("/api/refresh")
    async def api_refresh() -> dict[str, object]:
        counts = await refresh_cache()
        return {"status": "ok", **counts, "stats": database.get_stats()}

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "healthy",
            "database": database.health_check(),
            "collector": await collector_status(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/api/health")
    async def api_health() -> dict[str, object]:
        return await health()

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=int(os.getenv("CRON_UI_PORT", "8906")), reload=True)
