"""
Style Memory Engine — PR Shield's signature feature
Learns your team's coding style from merged PRs and builds
a reviewer persona that sounds like YOUR senior developer.

This is what makes PR Shield genuinely novel:
not generic AI feedback, but YOUR team's feedback.
"""

import json
import sqlite3
import os
import requests
import bleach
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pr_shield.db")
AIML_API_URL = "https://api.aimlapi.com/v1/chat/completions"


def sanitize_input(text: str) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned[:30_000]


def get_db():
    """Get database connection with parameterized query support."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_style_sample(
    team_id: str,
    diff: str,
    review_text: str,
    reviewer_name: str = "Senior Dev"
) -> bool:
    """
    Save a merged PR's diff + review as a style training sample.
    This teaches the system how YOUR team gives feedback.
    """
    # Sanitize everything before storing
    safe_team_id = bleach.clean(team_id, tags=[], strip=True)[:64]
    safe_diff = sanitize_input(diff)
    safe_review = sanitize_input(review_text)
    safe_name = bleach.clean(reviewer_name, tags=[], strip=True)[:128]

    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO style_samples (team_id, diff, review_text, reviewer_name)
               VALUES (?, ?, ?, ?)""",
            (safe_team_id, safe_diff, safe_review, safe_name),
        )
        conn.commit()
        conn.close()

        # Rebuild profile after each new sample
        rebuild_style_profile(safe_team_id)
        return True
    except Exception:
        return False


def rebuild_style_profile(team_id: str) -> Optional[dict]:
    """
    Re-analyze all style samples for a team and build a fresh profile.
    Called automatically after new samples are added.
    """
    api_key = os.environ.get("AIML_API_KEY", "")
    if not api_key:
        return None

    conn = get_db()
    rows = conn.execute(
        """SELECT diff, review_text, reviewer_name FROM style_samples
           WHERE team_id = ? ORDER BY created_at DESC LIMIT 10""",
        (team_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return None

    # Build a digest of examples for analysis
    examples = []
    for row in rows[:5]:  # Use most recent 5 for the profile
        examples.append(
            f"--- Example Review by {row['reviewer_name']} ---\n"
            f"Code changed:\n{row['diff'][:1500]}\n\n"
            f"Review given:\n{row['review_text'][:800]}\n"
        )

    examples_text = "\n\n".join(examples)

    system_prompt = """Analyze these code reviews to extract the reviewer's style profile.
Respond ONLY with valid JSON — no markdown, no preamble:
{
  "reviewer_name": "string",
  "communication_style": "string (e.g. 'direct and blunt', 'encouraging but rigorous')",
  "values": ["string (things they consistently care about)"],
  "pet_peeves": ["string (things they always flag)"],
  "sample_phrases": ["string (actual phrases they use)"],
  "summary": "string (2-sentence description of their review style)",
  "naming_conventions": "string",
  "test_expectations": "string",
  "comment_style": "string"
}"""

    try:
        response = requests.post(
            AIML_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze these reviews:\n\n{examples_text}"},
                ],
                "max_tokens": 800,
                "temperature": 0.2,
            },
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        profile = json.loads(raw)
        profile["sample_count"] = len(rows)

        # Store the built profile
        _save_profile(team_id, profile)
        return profile

    except Exception:
        return None


def get_style_profile(team_id: str) -> Optional[dict]:
    """Retrieve the current style profile for a team."""
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT profile_json FROM style_profiles WHERE team_id = ?",
            (team_id,),
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row["profile_json"])
        return None
    except Exception:
        return None


def _save_profile(team_id: str, profile: dict):
    """Save or update a team's style profile."""
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO style_profiles (team_id, profile_json, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)""",
        (team_id, json.dumps(profile)),
    )
    conn.commit()
    conn.close()


def get_sample_count(team_id: str) -> int:
    """How many style samples has this team contributed?"""
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) as n FROM style_samples WHERE team_id = ?",
            (team_id,),
        ).fetchone()
        conn.close()
        return row["n"] if row else 0
    except Exception:
        return 0
