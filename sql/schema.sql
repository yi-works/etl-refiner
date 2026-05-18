CREATE TABLE IF NOT EXISTS job_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT,
    status TEXT,
    started_at TEXT,
    error_message TEXT,
);

CREATE TABLE IF NOT EXISTS check_points(
    job_name TEXT PRIMARY KEY,
    last_value TEXT,
    update_at TEXT
);

CREATE TABLE IF NOT EXISTS locks (
    job_name TEXT PRIMARY KEY,
    locked_at TEXT
);