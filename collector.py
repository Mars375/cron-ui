"""OpenClaw cron API collector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


class CronCollector:
    def __init__(self, base_url: str = "http://localhost:8905", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=timeout)

    def health_check(self) -> dict[str, Any]:
        try:
            response = self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            payload = response.json() if response.content else {}
            return {
                "status": "healthy",
                "base_url": self.base_url,
                "detail": payload.get("status", "ok"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # pragma: no cover - defensive network fallback
            return {
                "status": "unhealthy",
                "base_url": self.base_url,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_jobs(self) -> list[dict[str, Any]]:
        raw = self._first_success_json([
            "/api/cron/jobs",
            "/api/jobs",
            "/cron/list",
            "/jobs",
        ])
        return [self._normalize_job(item) for item in self._extract_items(raw, keys=("jobs", "items", "data"))]

    def get_executions(self) -> list[dict[str, Any]]:
        raw = self._first_success_json([
            "/api/cron/executions",
            "/api/executions",
            "/cron/executions",
            "/executions",
        ])
        return [self._normalize_execution(item) for item in self._extract_items(raw, keys=("executions", "items", "data"))]

    def get_job_details(self, job_id: str) -> dict[str, Any] | None:
        for path in (f"/api/cron/jobs/{job_id}", f"/api/jobs/{job_id}", f"/cron/{job_id}"):
            try:
                response = self.client.get(f"{self.base_url}{path}")
                response.raise_for_status()
                return self._normalize_job(response.json())
            except Exception:
                continue
        return None

    def close(self) -> None:
        self.client.close()

    def _first_success_json(self, paths: list[str]) -> Any:
        for path in paths:
            try:
                response = self.client.get(f"{self.base_url}{path}")
                response.raise_for_status()
                return response.json()
            except Exception:
                continue
        return {}

    def _extract_items(self, raw: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            for key in keys:
                value = raw.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            # Some endpoints already return a single object under `item`
            item = raw.get("item")
            if isinstance(item, dict):
                return [item]
        return []

    def _normalize_job(self, raw: dict[str, Any]) -> dict[str, Any]:
        schedule = raw.get("schedule") or {}
        total_runs = int(raw.get("totalRuns") or raw.get("total_runs") or 0)
        failed_runs = int(raw.get("failedRuns") or raw.get("failed_runs") or 0)
        return {
            "job_id": str(raw.get("job_id") or raw.get("id") or raw.get("jobId") or raw.get("name") or ""),
            "name": str(raw.get("name") or raw.get("title") or raw.get("jobName") or "Unnamed job"),
            "description": str(raw.get("description") or ""),
            "enabled": bool(raw.get("enabled", True)),
            "status": str(raw.get("status") or self._derive_status(raw)),
            "schedule": schedule,
            "sessionTarget": raw.get("sessionTarget") or raw.get("session_target") or "",
            "totalRuns": total_runs,
            "failedRuns": failed_runs,
            "lastRun": self._stringify(raw.get("lastRun") or raw.get("last_run")),
            "nextRun": self._stringify(raw.get("nextRun") or raw.get("next_run")),
            "createdAt": self._stringify(raw.get("createdAt") or raw.get("created_at")),
            "updatedAt": self._stringify(raw.get("updatedAt") or raw.get("updated_at")),
            "tags": raw.get("tags") or [],
            "payload": raw.get("payload") or {},
            "delivery": raw.get("delivery") or {},
        }

    def _normalize_execution(self, raw: dict[str, Any]) -> dict[str, Any]:
        started = self._stringify(raw.get("startedAt") or raw.get("started_at"))
        completed = self._stringify(raw.get("completedAt") or raw.get("completed_at"))
        return {
            "execution_id": str(raw.get("execution_id") or raw.get("id") or raw.get("executionId") or ""),
            "job_id": str(raw.get("jobId") or raw.get("job_id") or ""),
            "job_name": str(raw.get("jobName") or raw.get("job_name") or ""),
            "status": str(raw.get("status") or "unknown"),
            "startedAt": started,
            "completedAt": completed,
            "durationMs": int(raw.get("durationMs") or raw.get("duration_ms") or 0),
            "result": raw.get("result") or {},
            "error": str(raw.get("error") or ""),
            "logs": str(raw.get("logs") or ""),
            "exitCode": int(raw.get("exitCode") or raw.get("exit_code") or 0),
            "success": bool(raw.get("success", False)),
        }

    def _derive_status(self, raw: dict[str, Any]) -> str:
        if not bool(raw.get("enabled", True)):
            return "disabled"
        total_runs = int(raw.get("totalRuns") or raw.get("total_runs") or 0)
        failed_runs = int(raw.get("failedRuns") or raw.get("failed_runs") or 0)
        if total_runs and failed_runs >= total_runs * 0.5:
            return "struggling"
        if failed_runs:
            return "failing"
        return "healthy"

    def _stringify(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return str(value)
