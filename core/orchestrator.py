"""
Band SDK Orchestrator — coordinates the three agents
Analyst → Security → Mentor pipeline with parallel execution where safe.

In a real Band SDK setup, each agent would be a registered service.
This implementation shows the collaboration pattern clearly.
"""

import time
import sqlite3
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from agents.analyst import analyze_pr
from agents.security import scan_security
from agents.mentor import write_review
from core.style_memory import get_style_profile

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pr_shield.db")


def run_review(
    diff: str,
    pr_title: str,
    pr_description: str,
    team_id: str = "default",
) -> dict:
    """
    Run the full PR Shield pipeline:
    1. Analyst understands intent (AI/ML API)
    2. Security scans for vulnerabilities (Featherless AI) — runs in parallel with Analyst
    3. Mentor synthesizes everything into personalized feedback (AI/ML API)

    Returns the complete review with all agent outputs.
    """
    start_time = time.time()
    style_profile = get_style_profile(team_id)

    # Step 1 & 2: Analyst and Security run in parallel
    # Security doesn't need analyst results to start scanning
    analyst_result = {}
    security_result = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        analyst_future = executor.submit(
            analyze_pr, diff, pr_title, pr_description, style_profile
        )
        security_future = executor.submit(
            scan_security, diff, None  # No analyst context yet — truly parallel
        )

        for future in as_completed([analyst_future, security_future]):
            if future == analyst_future:
                analyst_result = future.result()
            else:
                security_result = future.result()

    # Step 3: Mentor uses both results — must run after
    mentor_result = write_review(
        diff=diff,
        analyst_result=analyst_result,
        security_result=security_result,
        style_profile=style_profile,
    )

    elapsed = round(time.time() - start_time, 2)

    review = {
        "pr_title": pr_title,
        "team_id": team_id,
        "style_profile_active": style_profile is not None,
        "style_profile_name": style_profile.get("reviewer_name") if style_profile else None,
        "agents": {
            "analyst": analyst_result,
            "security": security_result,
            "mentor": mentor_result,
        },
        "overall_verdict": mentor_result.get("overall_verdict", "needs_discussion"),
        "security_gate": security_result.get("overall_risk", "review"),
        "elapsed_seconds": elapsed,
    }

    # Save to history
    _save_to_history(team_id, pr_title, analyst_result, security_result, mentor_result, review["overall_verdict"])

    return review


def _save_to_history(team_id, pr_title, analyst, security, mentor, verdict):
    """Persist review to audit log."""
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO review_history
               (team_id, pr_title, analyst_result, security_result, mentor_result, overall_verdict)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                team_id,
                pr_title,
                json.dumps(analyst),
                json.dumps(security),
                json.dumps(mentor),
                verdict,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # History is non-critical — don't break the review
