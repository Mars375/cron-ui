"""Comprehensive tests for collector module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from collector import CronCollector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_response():
    """Build a mock httpx.Response."""

    def _make(json_data=None, status_code=200, content=b""):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.content = content or b"{}"
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=resp
            )
        return resp

    return _make


@pytest.fixture
def collector():
    c = CronCollector(base_url="http://localhost:9999", timeout=3.0)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    def test_healthy(self, collector, mock_response):
        resp = mock_response(json_data={"status": "ok"}, content=b'{"status":"ok"}')
        with patch.object(collector.client, "get", return_value=resp):
            result = collector.health_check()
        assert result["status"] == "healthy"
        assert result["base_url"] == "http://localhost:9999"
        assert "timestamp" in result

    def test_unhealthy_on_error(self, collector):
        with patch.object(collector.client, "get", side_effect=httpx.ConnectError("refused")):
            result = collector.health_check()
        assert result["status"] == "unhealthy"
        assert "refused" in result["error"]


# ---------------------------------------------------------------------------
# get_jobs
# ---------------------------------------------------------------------------


class TestGetJobs:
    def test_with_jobs_list(self, collector, mock_response):
        data = {
            "jobs": [
                {
                    "id": "job-1",
                    "name": "Test Job",
                    "enabled": True,
                    "schedule": {"kind": "cron", "expr": "*/5 * * * *"},
                    "totalRuns": 10,
                    "failedRuns": 0,
                },
                {
                    "id": "job-2",
                    "name": "Failing Job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 60000},
                    "totalRuns": 20,
                    "failedRuns": 15,
                },
            ]
        }
        resp = mock_response(json_data=data, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            jobs = collector.get_jobs()
        assert len(jobs) == 2
        assert jobs[0]["job_id"] == "job-1"
        assert jobs[0]["name"] == "Test Job"
        assert jobs[1]["name"] == "Failing Job"

    def test_empty_response(self, collector, mock_response):
        resp = mock_response(json_data={}, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            jobs = collector.get_jobs()
        assert jobs == []

    def test_fallback_paths(self, collector, mock_response):
        """First 3 paths fail, 4th succeeds."""
        fail_resp = mock_response(status_code=404)
        ok_resp = mock_response(
            json_data={"jobs": [{"id": "late-job", "name": "Late"}]},
            content=b"{}",
        )
        call_count = 0

        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return fail_resp
            return ok_resp

        with patch.object(collector.client, "get", side_effect=side_effect):
            jobs = collector.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "late-job"


# ---------------------------------------------------------------------------
# get_executions
# ---------------------------------------------------------------------------


class TestGetExecutions:
    def test_with_executions(self, collector, mock_response):
        data = {
            "executions": [
                {
                    "id": "exec-a",
                    "jobId": "job-1",
                    "jobName": "job-1",
                    "status": "success",
                    "durationMs": 500,
                    "success": True,
                },
            ]
        }
        resp = mock_response(json_data=data, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            execs = collector.get_executions()
        assert len(execs) == 1
        assert execs[0]["execution_id"] == "exec-a"
        assert execs[0]["success"] is True

    def test_raw_list_format(self, collector, mock_response):
        """API returns a flat list instead of wrapped dict."""
        data = [
            {"id": "e1", "jobId": "j1", "status": "success", "success": True},
        ]
        resp = mock_response(json_data=data, content=b"[]")
        with patch.object(collector.client, "get", return_value=resp):
            execs = collector.get_executions()
        assert len(execs) == 1
        assert execs[0]["execution_id"] == "e1"


# ---------------------------------------------------------------------------
# get_job_details
# ---------------------------------------------------------------------------


class TestGetJobDetails:
    def test_found(self, collector, mock_response):
        resp = mock_response(
            json_data={"id": "job-x", "name": "Job X", "enabled": True},
            content=b"{}",
        )
        with patch.object(collector.client, "get", return_value=resp):
            job = collector.get_job_details("job-x")
        assert job is not None
        assert job["job_id"] == "job-x"

    def test_not_found(self, collector, mock_response):
        fail_resp = mock_response(status_code=404)
        with patch.object(collector.client, "get", return_value=fail_resp):
            job = collector.get_job_details("nonexistent")
        assert job is None


# ---------------------------------------------------------------------------
# _extract_items edge cases
# ---------------------------------------------------------------------------


class TestExtractItems:
    def test_single_item_key(self, collector, mock_response):
        data = {"item": {"id": "single", "name": "One"}}
        resp = mock_response(json_data=data, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            jobs = collector.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "single"

    def test_data_key(self, collector, mock_response):
        data = {"data": [{"id": "d1"}, {"id": "d2"}]}
        resp = mock_response(json_data=data, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            jobs = collector.get_jobs()
        assert len(jobs) == 2

    def test_non_dict_items_filtered(self, collector, mock_response):
        data = {"jobs": [{"id": "ok"}, "string", 42, None]}
        resp = mock_response(json_data=data, content=b"{}")
        with patch.object(collector.client, "get", return_value=resp):
            jobs = collector.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "ok"


# ---------------------------------------------------------------------------
# _normalize_job edge cases
# ---------------------------------------------------------------------------


class TestNormalizeJob:
    def test_minimal_job(self, collector):
        job = collector._normalize_job({})
        assert job["job_id"] == ""
        assert job["name"] == "Unnamed job"
        assert job["enabled"] is True
        assert job["status"] == "healthy"

    def test_alternative_field_names(self, collector):
        job = collector._normalize_job(
            {
                "jobId": "alt-id",
                "title": "Alt Title",
                "total_runs": 100,
                "failed_runs": 60,
            }
        )
        assert job["job_id"] == "alt-id"
        assert job["name"] == "Alt Title"
        assert job["status"] == "struggling"  # 60% failure rate

    def test_disabled_job(self, collector):
        job = collector._normalize_job({"id": "x", "enabled": False})
        assert job["status"] == "disabled"

    def test_failing_job(self, collector):
        job = collector._normalize_job(
            {"id": "y", "enabled": True, "totalRuns": 10, "failedRuns": 2}
        )
        assert job["status"] == "failing"

    def test_with_all_fields(self, collector):
        job = collector._normalize_job(
            {
                "id": "full-job",
                "name": "Full Job",
                "description": "A job with everything",
                "enabled": True,
                "status": "custom-status",
                "schedule": {"kind": "cron", "expr": "0 * * * *", "tz": "UTC"},
                "sessionTarget": "isolated",
                "totalRuns": 50,
                "failedRuns": 1,
                "lastRun": "2026-01-01T00:00:00Z",
                "nextRun": "2026-01-01T01:00:00Z",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2026-01-01T00:00:00Z",
                "tags": ["alpha"],
                "payload": {"kind": "systemEvent", "text": "hello"},
                "delivery": {"mode": "announce"},
            }
        )
        assert job["job_id"] == "full-job"
        assert job["description"] == "A job with everything"
        assert job["schedule"]["expr"] == "0 * * * *"
        assert job["sessionTarget"] == "isolated"
        assert job["tags"] == ["alpha"]
        assert job["payload"]["kind"] == "systemEvent"


# ---------------------------------------------------------------------------
# _normalize_execution edge cases
# ---------------------------------------------------------------------------


class TestNormalizeExecution:
    def test_minimal_execution(self, collector):
        ex = collector._normalize_execution({})
        assert ex["execution_id"] == ""
        assert ex["success"] is False
        assert ex["durationMs"] == 0

    def test_alternative_field_names(self, collector):
        ex = collector._normalize_execution(
            {
                "executionId": "ex-alt",
                "job_id": "j-alt",
                "job_name": "J Alt",
                "started_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T00:01:00Z",
                "duration_ms": 60000,
                "exit_code": 0,
                "success": True,
            }
        )
        assert ex["execution_id"] == "ex-alt"
        assert ex["job_id"] == "j-alt"
        assert ex["durationMs"] == 60000
        assert ex["success"] is True

    def test_with_datetime_object(self, collector):
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        ex = collector._normalize_execution({"id": "dt-ex", "startedAt": dt})
        assert ex["startedAt"] is not None
        assert "2026-06-15" in ex["startedAt"]


# ---------------------------------------------------------------------------
# _stringify
# ---------------------------------------------------------------------------


class TestStringify:
    def test_none(self, collector):
        assert collector._stringify(None) is None

    def test_empty_string(self, collector):
        assert collector._stringify("") is None

    def test_datetime(self, collector):
        dt = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = collector._stringify(dt)
        assert "2026-01-01" in result

    def test_regular_string(self, collector):
        assert collector._stringify("hello") == "hello"


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    def test_close(self, collector):
        with patch.object(collector.client, "close"):
            collector.close()
            collector.client.close.assert_called_once()
