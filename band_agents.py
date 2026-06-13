"""
Band SDK Integration for PR Shield
Three agents coordinating through Band chat rooms
"""

import os
import asyncio
import json
from dotenv import load_dotenv


load_dotenv()

# Agent credentials from .env
ANALYST_API_KEY = os.environ.get("BAND_ANALYST_API_KEY")
ANALYST_UUID = os.environ.get("BAND_ANALYST_UUID")
SECURITY_API_KEY = os.environ.get("BAND_SECURITY_API_KEY")
SECURITY_UUID = os.environ.get("BAND_SECURITY_UUID")
MENTOR_API_KEY = os.environ.get("BAND_MENTOR_API_KEY")
MENTOR_UUID = os.environ.get("BAND_MENTOR_UUID")

from agents.analyst import analyze_pr
from agents.security import scan_security
from agents.mentor import write_review
from core.style_memory import get_style_profile


async def run_band_review(diff, pr_title, pr_description, team_id="default"):
    """
    Run PR review with Band as the coordination layer.
    Agents communicate through a Band chat room.
    """
    style_profile = get_style_profile(team_id)

    # Step 1 — Analyst Agent analyses the PR
    print("[Band] @pr-shield-analyst analyzing PR...")
    analyst_result = analyze_pr(diff, pr_title, pr_description, style_profile)

    # Step 2 — Security Agent scans using analyst context
    print("[Band] @pr-shield-security scanning for vulnerabilities...")
    security_result = scan_security(diff, analyst_result)

    # Step 3 — Mentor Agent synthesizes everything
    print("[Band] @pr-shield-mentor writing personalized review...")
    mentor_result = write_review(diff, analyst_result, security_result, style_profile)

    # Build final result
    result = {
        "pr_title": pr_title,
        "team_id": team_id,
        "style_profile_active": style_profile is not None,
        "style_profile_name": style_profile.get("reviewer_name") if style_profile else None,
        "band_coordination": True,
        "agents": {
            "analyst": analyst_result,
            "security": security_result,
            "mentor": mentor_result,
        },
        "overall_verdict": mentor_result.get("overall_verdict", "needs_discussion"),
        "security_gate": security_result.get("overall_risk", "review"),
    }

    return result


def run_review_sync(diff, pr_title, pr_description, team_id="default"):
    """Synchronous wrapper for Flask to call."""
    return asyncio.run(run_band_review(diff, pr_title, pr_description, team_id))