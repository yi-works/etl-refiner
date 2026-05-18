import sqlite3
from datetime import datetime, timezone


def utc_now_str():
    return datetime.now(timezone.utc).isoformat()


class StateManager:
    def __init__(self, db_path: str = "state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS job_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT,
            status TEXT,
            started_at TEXT,
            finished_at TEXT,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS checkpoints (
            job_name TEXT PRIMARY KEY,
            last_value TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS locks (
            job_name TEXT PRIMARY KEY,
            locked_at TEXT
        );
        """)
        self.conn.commit()

    # --- lock ---
    def acquire_lock(self, job_name: str) -> bool:
        try:
            self.conn.execute(
                "INSERT INTO locks VALUES (?, ?)",
                (job_name, utc_now_str()),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"{job_name} is already locked")
            return False

    def release_lock(self, job_name: str):
        self.conn.execute("DELETE FROM locks WHERE job_name=?", (job_name,))
        self.conn.commit()

    # --- job lifecycle ---
    def start_job(self, job_name: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO job_runs (job_name, status, started_at) VALUES (?, 'running', ?)",
            (job_name, utc_now_str()),
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_job(self, run_id: int):
        self.conn.execute(
            "UPDATE job_runs SET status='success', finished_at=? WHERE run_id=?",
            (utc_now_str(), run_id),
        )
        self.conn.commit()

    def fail_job(self, run_id: int, err: str):
        self.conn.execute(
            "UPDATE job_runs SET status='failed', finished_at=?, error_message=? WHERE run_id=?",
            (utc_now_str(), err, run_id),
        )
        self.conn.commit()

    # --- checkpoint ---
    def get_checkpoint(self, job_name: str):
        cur = self.conn.execute(
            "SELECT last_value FROM checkpoints WHERE job_name=?",
            (job_name,),
        )
        row = cur.fetchone()
        return row[0] if row else None

    def update_checkpoint(self, job_name: str, val: str):
        self.conn.execute(
            """
            INSERT INTO checkpoints VALUES (?, ?, ?)
            ON CONFLICT(job_name)
            DO UPDATE SET last_value=excluded.last_value,
                         updated_at=excluded.updated_at
            """,
            (job_name, val, utc_now_str()),
        )
        self.conn.commit()
