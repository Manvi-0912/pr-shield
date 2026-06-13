"""
Initialize the PR Shield SQLite database.
Run once: python core/init_db.py
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pr_shield.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Style training samples
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS style_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            diff TEXT NOT NULL,
            review_text TEXT NOT NULL,
            reviewer_name TEXT DEFAULT 'Senior Dev',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Computed style profiles
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS style_profiles (
            team_id TEXT PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PR review history (for audit trail)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            pr_title TEXT,
            analyst_result TEXT,
            security_result TEXT,
            mentor_result TEXT,
            overall_verdict TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_team ON style_samples(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_team ON review_history(team_id)")

    conn.commit()
    conn.close()
    print("✅ Database initialized at:", DB_PATH)


if __name__ == "__main__":
    init_db()
