from fastapi.testclient import TestClient

from app import create_app


class DummyCollector:
    def get_jobs(self):
        return []

    def get_executions(self):
        return []

    def health_check(self):
        return {"status": "healthy", "base_url": "dummy"}


def test_app_smoke(tmp_path):
    app = create_app(tmp_path / "cron-ui.sqlite3", collector=DummyCollector())
    with TestClient(app) as client:
        dashboard = client.get("/")
        jobs = client.get("/jobs")
        stats = client.get("/api/stats")
        health = client.get("/health")

    assert dashboard.status_code == 200
    assert jobs.status_code == 200
    assert stats.status_code == 200
    assert stats.json()["job_count"] >= 3
    assert health.status_code == 200
