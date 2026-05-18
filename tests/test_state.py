import pytest
from pipeline.state import StateManager


@pytest.fixture
def sm():
    return StateManager(":memory:")


def test_acquire_lock(sm):
    assert sm.acquire_lock("job1") is True
    assert sm.acquire_lock("job1") is False


def test_release_lock(sm):
    sm.acquire_lock("job1")
    sm.release_lock("job1")

    # 再取得できること
    assert sm.acquire_lock("job1") is True


def test_job_success(sm):
    run_id = sm.start_job("job1")

    sm.finish_job(run_id)

    row = sm.conn.execute(
        "SELECT status FROM job_runs WHERE run_id=?", (run_id,)
    ).fetchone()

    assert row[0] == "success"


def test_job_fail(sm):
    run_id = sm.start_job("job1")

    sm.fail_job(run_id, "error")

    row = sm.conn.execute(
        "SELECT status, error_message FROM job_runs WHERE run_id=?", (run_id,)
    ).fetchone()

    assert row[0] == "failed"
    assert row[1] == "error"


def test_checkpoint(sm):
    # 初期はNone
    assert sm.get_checkpoint("job1") is None

    sm.update_checkpoint("job1", "2026-05-08")

    assert sm.get_checkpoint("job1") == "2026-05-08"


def test_multiple_runs(sm):
    sm.start_job("job1")
    sm.start_job("job1")

    count = sm.conn.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0]

    assert count == 2


def test_lock_table_content(sm):
    sm.acquire_lock("job1")

    rows = list(sm.conn.execute("SELECT * FROM locks"))

    assert len(rows) == 1
    assert rows[0][0] == "job1"


def test_tables_exist(sm):
    tables = {
        row[0]
        for row in sm.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    assert "job_runs" in tables


def test_full_flow(sm):
    # lock
    sm.acquire_lock("job1")

    print("After lock:")
    print(list(sm.conn.execute("SELECT * FROM locks")))

    # job start
    run_id = sm.start_job("job1")

    print("After start_job:")
    print(list(sm.conn.execute("SELECT * FROM job_runs")))

    # finish
    sm.finish_job(run_id)

    print("After finish:")
    print(list(sm.conn.execute("SELECT * FROM job_runs")))

    # assert
    status = sm.conn.execute(
        "SELECT status FROM job_runs WHERE run_id=?", (run_id,)
    ).fetchone()[0]

    assert status == "success"
