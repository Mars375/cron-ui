from collector import CronCollector


def test_collector_normalization():
    collector = CronCollector(base_url="http://localhost:1")
    job = collector._normalize_job(
        {
            "id": "labs-foo",
            "name": "labs-foo",
            "enabled": True,
            "schedule": {"kind": "cron", "expr": "*/10 * * * *", "tz": "UTC"},
            "totalRuns": 10,
            "failedRuns": 0,
        }
    )
    execution = collector._normalize_execution(
        {
            "id": "exec-1",
            "jobId": "labs-foo",
            "jobName": "labs-foo",
            "status": "success",
            "durationMs": 42,
            "success": True,
        }
    )
    assert job["job_id"] == "labs-foo"
    assert job["status"] == "healthy"
    assert execution["execution_id"] == "exec-1"
    assert execution["success"] is True
    collector.close()
