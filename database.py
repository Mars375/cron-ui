"""SQLite storage for cron-ui."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class CronDatabase:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS cron_jobs (
            job_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'unknown',
            schedule_json TEXT NOT NULL DEFAULT '{}',
            schedule_type TEXT DEFAULT '',
            schedule_expression TEXT DEFAULT '',
            schedule_timezone TEXT DEFAULT '',
            session_target TEXT DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}',
            delivery_json TEXT NOT NULL DEFAULT '{}',
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT,
            last_run_at TEXT,
            next_run_at TEXT,
            total_runs INTEGER NOT NULL DEFAULT 0,
            failed_runs INTEGER NOT NULL DEFAULT 0,
            success_rate REAL NOT NULL DEFAULT 0,
            last_sync_at TEXT NOT NULL,
            raw_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS executions (
            execution_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            job_name TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'unknown',
            started_at TEXT,
            completed_at TEXT,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT DEFAULT '',
            logs TEXT DEFAULT '',
            exit_code INTEGER NOT NULL DEFAULT 0,
            success INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            raw_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(job_id) REFERENCES cron_jobs(job_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_executions_job_id ON executions(job_id);
        CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
        CREATE INDEX IF NOT EXISTS idx_executions_started_at ON executions(started_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_status ON cron_jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_updated_at ON cron_jobs(updated_at);
        """
        with closing(self._connect()) as conn:
            conn.executescript(schema)
            conn.commit()

    def store_job(self, job: dict[str, Any]) -> None:
        row = self._normalize_job(job)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO cron_jobs (
                    job_id, name, description, enabled, status,
                    schedule_json, schedule_type, schedule_expression, schedule_timezone,
                    session_target, payload_json, delivery_json, tags_json,
                    created_at, updated_at, last_run_at, next_run_at,
                    total_runs, failed_runs, success_rate, last_sync_at, raw_json
                ) VALUES (
                    :job_id, :name, :description, :enabled, :status,
                    :schedule_json, :schedule_type, :schedule_expression, :schedule_timezone,
                    :session_target, :payload_json, :delivery_json, :tags_json,
                    :created_at, :updated_at, :last_run_at, :next_run_at,
                    :total_runs, :failed_runs, :success_rate, :last_sync_at, :raw_json
                )
                ON CONFLICT(job_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    enabled=excluded.enabled,
                    status=excluded.status,
                    schedule_json=excluded.schedule_json,
                    schedule_type=excluded.schedule_type,
                    schedule_expression=excluded.schedule_expression,
                    schedule_timezone=excluded.schedule_timezone,
                    session_target=excluded.session_target,
                    payload_json=excluded.payload_json,
                    delivery_json=excluded.delivery_json,
                    tags_json=excluded.tags_json,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    last_run_at=excluded.last_run_at,
                    next_run_at=excluded.next_run_at,
                    total_runs=excluded.total_runs,
                    failed_runs=excluded.failed_runs,
                    success_rate=excluded.success_rate,
                    last_sync_at=excluded.last_sync_at,
                    raw_json=excluded.raw_json
                """,
                row,
            )
            conn.commit()

    def store_execution(self, execution: dict[str, Any]) -> None:
        row = self._normalize_execution(execution)
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO executions (
                    execution_id, job_id, job_name, status,
                    started_at, completed_at, duration_ms, result_json,
                    error, logs, exit_code, success, created_at, raw_json
                ) VALUES (
                    :execution_id, :job_id, :job_name, :status,
                    :started_at, :completed_at, :duration_ms, :result_json,
                    :error, :logs, :exit_code, :success, :created_at, :raw_json
                )
                ON CONFLICT(execution_id) DO UPDATE SET
                    job_id=excluded.job_id,
                    job_name=excluded.job_name,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    duration_ms=excluded.duration_ms,
                    result_json=excluded.result_json,
                    error=excluded.error,
                    logs=excluded.logs,
                    exit_code=excluded.exit_code,
                    success=excluded.success,
                    created_at=excluded.created_at,
                    raw_json=excluded.raw_json
                """,
                row,
            )
            conn.commit()

    def get_all_jobs(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM cron_jobs ORDER BY COALESCE(updated_at, last_sync_at) DESC, name ASC"
            ).fetchall()
        jobs = [self._job_from_row(row) for row in rows]
        for job in jobs:
            recent = self.get_job_executions(job["job_id"], limit=1)
            job["last_execution"] = recent[0] if recent else None
        return jobs

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM cron_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        job = self._job_from_row(row)
        job["recent_executions"] = self.get_job_executions(job_id, limit=25)
        return job

    def get_job_executions(self, job_id: str, limit: int = 25) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM executions
                WHERE job_id = ?
                ORDER BY COALESCE(started_at, created_at) DESC, execution_id DESC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [self._execution_from_row(row) for row in rows]

    def get_executions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT * FROM executions
                ORDER BY COALESCE(started_at, created_at) DESC, execution_id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._execution_from_row(row) for row in rows]

    def get_recent_executions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.get_executions(limit=limit, offset=0)

    def get_failed_jobs(self, limit: int = 5) -> list[dict[str, Any]]:
        jobs = [job for job in self.get_all_jobs() if job["status"] in {"failing", "struggling", "failed"}]
        return jobs[:limit]

    def get_stats(self) -> dict[str, Any]:
        with closing(self._connect()) as conn:
            job_count = conn.execute("SELECT COUNT(*) FROM cron_jobs").fetchone()[0]
            enabled_count = conn.execute("SELECT COUNT(*) FROM cron_jobs WHERE enabled = 1").fetchone()[0]
            disabled_count = conn.execute("SELECT COUNT(*) FROM cron_jobs WHERE enabled = 0").fetchone()[0]
            execution_count = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
            success_count = conn.execute("SELECT COUNT(*) FROM executions WHERE success = 1").fetchone()[0]
            failure_count = conn.execute("SELECT COUNT(*) FROM executions WHERE success = 0").fetchone()[0]
            failing_jobs = conn.execute(
                "SELECT COUNT(*) FROM cron_jobs WHERE status IN ('failing', 'struggling', 'failed')"
            ).fetchone()[0]
            last_sync = conn.execute("SELECT MAX(last_sync_at) FROM cron_jobs").fetchone()[0]

        success_rate = round((success_count / execution_count) * 100, 1) if execution_count else 0.0
        return {
            "job_count": job_count,
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
            "execution_count": execution_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "failing_jobs": failing_jobs,
            "success_rate": success_rate,
            "last_sync_at": last_sync,
        }

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "healthy" if self.db_path.exists() else "missing",
            "path": str(self.db_path),
            "exists": self.db_path.exists(),
        }

    def job_count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM cron_jobs").fetchone()[0]

    def execution_count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]

    def seed_demo_data(self) -> None:
        if self.job_count() > 0:
            return

        now = datetime.now(timezone.utc)
        demo_jobs = [
            {
                "job_id": "labs-cron-watcher",
                "name": "labs-cron-watcher",
                "description": "Surveille les crons Labs et alerte sur les échecs répétés.",
                "enabled": True,
                "status": "healthy",
                "schedule": {"kind": "cron", "expr": "*/30 * * * *", "tz": "Europe/Paris"},
                "sessionTarget": "main",
                "totalRuns": 42,
                "failedRuns": 1,
                "lastRun": now.isoformat(),
                "nextRun": now.isoformat(),
                "tags": ["monitoring", "labs"],
            },
            {
                "job_id": "labs-forge",
                "name": "labs-forge",
                "description": "Sélectionne et lance les chantiers prioritaires.",
                "enabled": True,
                "status": "failing",
                "schedule": {"kind": "cron", "expr": "15 * * * *", "tz": "Europe/Paris"},
                "sessionTarget": "main",
                "totalRuns": 18,
                "failedRuns": 5,
                "lastRun": now.isoformat(),
                "nextRun": now.isoformat(),
                "tags": ["forge", "dispatch"],
            },
            {
                "job_id": "labs-git-autopush",
                "name": "labs-git-autopush",
                "description": "Prépare les projets promouvables et pousse les repos clean.",
                "enabled": False,
                "status": "disabled",
                "schedule": {"kind": "cron", "expr": "0 3 * * *", "tz": "Europe/Paris"},
                "sessionTarget": "main",
                "totalRuns": 4,
                "failedRuns": 0,
                "lastRun": now.isoformat(),
                "nextRun": None,
                "tags": ["git", "promotion"],
            },
        ]
        demo_executions = [
            {
                "execution_id": "exec-001",
                "job_id": "labs-forge",
                "job_name": "labs-forge",
                "status": "failed",
                "startedAt": now.isoformat(),
                "completedAt": now.isoformat(),
                "durationMs": 1840,
                "error": "No active issue selected",
                "logs": "Phase PROTOTYPE still in progress",
                "exitCode": 1,
                "success": False,
            },
            {
                "execution_id": "exec-002",
                "job_id": "labs-cron-watcher",
                "job_name": "labs-cron-watcher",
                "status": "success",
                "startedAt": now.isoformat(),
                "completedAt": now.isoformat(),
                "durationMs": 620,
                "logs": "Health check ok",
                "exitCode": 0,
                "success": True,
            },
            {
                "execution_id": "exec-003",
                "job_id": "labs-git-autopush",
                "job_name": "labs-git-autopush",
                "status": "success",
                "startedAt": now.isoformat(),
                "completedAt": now.isoformat(),
                "durationMs": 1120,
                "logs": "No work queued",
                "exitCode": 0,
                "success": True,
            },
        ]
        for job in demo_jobs:
            self.store_job(job)
        for execution in demo_executions:
            self.store_execution(execution)

    def _normalize_job(self, job: dict[str, Any]) -> dict[str, Any]:
        raw = dict(job)
        job_id = str(raw.get("job_id") or raw.get("id") or raw.get("jobId") or raw.get("name") or "")
        schedule = raw.get("schedule") or {}
        total_runs = int(raw.get("totalRuns") or raw.get("total_runs") or 0)
        failed_runs = int(raw.get("failedRuns") or raw.get("failed_runs") or 0)
        success_rate = round(((total_runs - failed_runs) / total_runs) * 100, 1) if total_runs else 0.0
        now = datetime.now(timezone.utc).isoformat()
        return {
            "job_id": job_id,
            "name": str(raw.get("name") or raw.get("title") or job_id or "Unnamed job"),
            "description": str(raw.get("description") or ""),
            "enabled": 1 if bool(raw.get("enabled", True)) else 0,
            "status": str(raw.get("status") or self._derive_status(raw)),
            "schedule_json": json.dumps(schedule, ensure_ascii=False),
            "schedule_type": str(schedule.get("kind") or raw.get("schedule_type") or ""),
            "schedule_expression": str(schedule.get("expr") or raw.get("schedule_expression") or ""),
            "schedule_timezone": str(schedule.get("tz") or raw.get("schedule_timezone") or ""),
            "session_target": str(raw.get("sessionTarget") or raw.get("session_target") or ""),
            "payload_json": json.dumps(raw.get("payload") or {}, ensure_ascii=False),
            "delivery_json": json.dumps(raw.get("delivery") or {}, ensure_ascii=False),
            "tags_json": json.dumps(raw.get("tags") or [], ensure_ascii=False),
            "created_at": self._stringify(raw.get("createdAt") or raw.get("created_at")),
            "updated_at": self._stringify(raw.get("updatedAt") or raw.get("updated_at")),
            "last_run_at": self._stringify(raw.get("lastRun") or raw.get("last_run")),
            "next_run_at": self._stringify(raw.get("nextRun") or raw.get("next_run")),
            "total_runs": total_runs,
            "failed_runs": failed_runs,
            "success_rate": success_rate,
            "last_sync_at": now,
            "raw_json": json.dumps(raw, ensure_ascii=False, default=str),
        }

    def _normalize_execution(self, execution: dict[str, Any]) -> dict[str, Any]:
        raw = dict(execution)
        execution_id = str(raw.get("execution_id") or raw.get("id") or raw.get("executionId") or "")
        started = self._stringify(raw.get("startedAt") or raw.get("started_at"))
        completed = self._stringify(raw.get("completedAt") or raw.get("completed_at"))
        return {
            "execution_id": execution_id,
            "job_id": str(raw.get("jobId") or raw.get("job_id") or ""),
            "job_name": str(raw.get("jobName") or raw.get("job_name") or ""),
            "status": str(raw.get("status") or "unknown"),
            "started_at": started,
            "completed_at": completed,
            "duration_ms": int(raw.get("durationMs") or raw.get("duration_ms") or 0),
            "result_json": json.dumps(raw.get("result") or {}, ensure_ascii=False),
            "error": str(raw.get("error") or ""),
            "logs": str(raw.get("logs") or ""),
            "exit_code": int(raw.get("exitCode") or raw.get("exit_code") or 0),
            "success": 1 if bool(raw.get("success")) else 0,
            "created_at": self._stringify(raw.get("createdAt") or raw.get("created_at") or started or datetime.now(timezone.utc).isoformat()),
            "raw_json": json.dumps(raw, ensure_ascii=False, default=str),
        }

    def _job_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": row["job_id"],
            "name": row["name"],
            "description": row["description"],
            "enabled": bool(row["enabled"]),
            "status": row["status"],
            "schedule": json.loads(row["schedule_json"] or "{}"),
            "schedule_type": row["schedule_type"],
            "schedule_expression": row["schedule_expression"],
            "schedule_timezone": row["schedule_timezone"],
            "session_target": row["session_target"],
            "payload": json.loads(row["payload_json"] or "{}"),
            "delivery": json.loads(row["delivery_json"] or "{}"),
            "tags": json.loads(row["tags_json"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_run_at": row["last_run_at"],
            "next_run_at": row["next_run_at"],
            "total_runs": row["total_runs"],
            "failed_runs": row["failed_runs"],
            "success_rate": row["success_rate"],
            "last_sync_at": row["last_sync_at"],
            "raw": json.loads(row["raw_json"] or "{}"),
        }

    def _execution_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "execution_id": row["execution_id"],
            "job_id": row["job_id"],
            "job_name": row["job_name"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "duration_ms": row["duration_ms"],
            "result": json.loads(row["result_json"] or "{}"),
            "error": row["error"],
            "logs": row["logs"],
            "exit_code": row["exit_code"],
            "success": bool(row["success"]),
            "created_at": row["created_at"],
            "raw": json.loads(row["raw_json"] or "{}"),
        }

    def _derive_status(self, job: dict[str, Any]) -> str:
        if not bool(job.get("enabled", True)):
            return "disabled"
        total_runs = int(job.get("totalRuns") or job.get("total_runs") or 0)
        failed_runs = int(job.get("failedRuns") or job.get("failed_runs") or 0)
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
