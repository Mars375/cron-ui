"""Comprehensive tests for app module — all routes and edge cases."""

from __future__ import annotations

import time

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import create_app


# ---------------------------------------------------------------------------
# Test collector mock
# ---------------------------------------------------------------------------


class DummyCollector:
    """Collector that returns predictable data without network calls."""

    def __init__(self, jobs=None, executions=None):
        self._jobs = jobs or []
        self._executions = executions or []

    def get_jobs(self):
        return self._jobs

    def get_executions(self):
        return self._executions

    def get_job_details(self, job_id):
        for j in self._jobs:
            if j.get("job_id") == job_id or j.get("id") == job_id:
                return j
        return None

    def health_check(self):
        return {"status": "healthy", "base_url": "http://test"}

    def close(self):
        pass


def _make_job(job_id, name=None, status="healthy", enabled=True, **kw):
    return {
        "job_id": job_id,
        "name": name or job_id,
        "description": kw.get("description", ""),
        "enabled": enabled,
        "status": status,
        "schedule": {"kind": "cron", "expr": "*/5 * * * *", "tz": "UTC"},
        "totalRuns": kw.get("total_runs", 10),
        "failedRuns": kw.get("failed_runs", 0),
        **{k: v for k, v in kw.items() if k not in ("total_runs", "failed_runs")},
    }


def _make_exec(exec_id, job_id, success=True, duration=500):
    return {
        "execution_id": exec_id,
        "job_id": job_id,
        "job_name": job_id,
        "status": "success" if success else "failed",
        "durationMs": duration,
        "success": success,
    }


# ---------------------------------------------------------------------------
# Dashboard and page routes
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_renders(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert b"html" in resp.content.lower()


class TestJobsPage:
    def test_jobs_list(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/jobs")
        assert resp.status_code == 200

    def test_jobs_filter_by_status(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            # Seed data first
            client.post("/api/refresh")
            resp = client.get("/jobs?status=failing")
        assert resp.status_code == 200

    def test_jobs_search_query(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            client.post("/api/refresh")
            resp = client.get("/jobs?q=forge")
        assert resp.status_code == 200


class TestJobDetail:
    def test_job_detail_found(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            # Seed demo data
            client.post("/api/refresh")
            resp = client.get("/jobs/labs-forge")
        assert resp.status_code == 200

    def test_job_detail_404(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/jobs/nonexistent-job")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


class TestApiStats:
    def test_stats_structure(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "job_count" in data
        assert "success_rate" in data
        assert "execution_count" in data


class TestApiJobs:
    def test_list_jobs(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert "count" in data

    def test_get_single_job(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            client.post("/api/refresh")
            resp = client.get("/api/jobs/labs-forge")
        assert resp.status_code == 200
        assert resp.json()["job_id"] == "labs-forge"

    def test_get_single_job_404(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/jobs/nope")
        assert resp.status_code == 404


class TestApiExecutions:
    def test_list_executions(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/executions")
        assert resp.status_code == 200
        data = resp.json()
        assert "executions" in data
        assert "count" in data

    def test_executions_with_pagination(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/executions?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 10
        assert data["offset"] == 0


class TestApiRefresh:
    def test_refresh_endpoint(self, tmp_path):
        collector = DummyCollector()
        app = create_app(tmp_path / "test.db", collector=collector)
        with TestClient(app) as client:
            resp = client.post("/api/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_refresh_with_live_data(self, tmp_path):
        jobs = [_make_job("live-1", "Live Job")]
        execs = [_make_exec("e1", "live-1")]
        collector = DummyCollector(jobs=jobs, executions=execs)
        app = create_app(tmp_path / "test.db", collector=collector)
        with TestClient(app) as client:
            resp = client.post("/api/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jobs"] == 1
        assert data["executions"] == 1


class TestHealthEndpoints:
    def test_health(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "collector" in data

    def test_api_health(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=DummyCollector())
        with TestClient(app) as client:
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class SlowCollector(DummyCollector):
    def get_jobs(self):
        time.sleep(0.2)
        return super().get_jobs()

    def get_executions(self):
        time.sleep(0.2)
        return super().get_executions()


class TestStartupResilience:
    def test_startup_timeout_falls_back_to_demo_data(self, tmp_path):
        app = create_app(tmp_path / "test.db", collector=SlowCollector(), startup_refresh_timeout=0.05)
        with TestClient(app) as client:
            health = client.get("/health")
            stats = client.get("/api/stats")
        assert health.status_code == 200
        assert stats.status_code == 200
        assert stats.json()["job_count"] >= 1
