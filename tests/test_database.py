from database import CronDatabase


def test_database_seed_and_stats(tmp_path):
    db = CronDatabase(tmp_path / "cron-ui.sqlite3")
    db.initialize()
    assert db.job_count() == 0

    db.seed_demo_data()
    assert db.job_count() == 3
    assert db.execution_count() == 3

    stats = db.get_stats()
    assert stats["job_count"] == 3
    assert stats["enabled_count"] == 2
    assert stats["failing_jobs"] >= 1

    job = db.get_job("labs-forge")
    assert job is not None
    assert job["name"] == "labs-forge"
    assert job["recent_executions"]

    jobs = db.get_failed_jobs()
    assert jobs

    db.store_job(
        {
            "job_id": "custom-job",
            "name": "custom-job",
            "enabled": True,
            "status": "healthy",
            "schedule": {"kind": "cron", "expr": "*/5 * * * *", "tz": "UTC"},
            "totalRuns": 10,
            "failedRuns": 0,
        }
    )
    db.store_execution(
        {
            "execution_id": "exec-999",
            "job_id": "custom-job",
            "job_name": "custom-job",
            "status": "success",
            "durationMs": 100,
            "success": True,
        }
    )
    assert db.job_count() == 4
    assert db.execution_count() == 4
