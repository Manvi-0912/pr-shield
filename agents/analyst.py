"""
Analyst Agent — powered by AI/ML API (GPT-4o)
Role: Understand the PR's purpose, map changes to goals,
      identify what problem the developer was solving.
"""

import os
import json
import requests
import bleach
from typing import Optional


AIML_API_URL = "https://api.aimlapi.com/v1/chat/completions"
MODEL = "gpt-4o"  # AI/ML API model


def sanitize_input(text: str) -> str:
    """Strip HTML and limit length to prevent injection."""
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned[:50_000]  # Hard cap at 50k chars


def analyze_pr(
    diff: str,
    pr_title: str,
    pr_description: str,
    style_profile: Optional[dict] = None,
) -> dict:
    """
    Analyze a PR diff and return structured intent analysis.

    Returns:
        {
            "summary": str,           # One-paragraph plain-English summary
            "intent": str,            # What the developer was trying to do
            "key_changes": list[str], # Bullet list of significant changes
            "complexity": str,        # "low" | "medium" | "high"
            "risk_areas": list[str],  # Areas that deserve extra scrutiny
            "agent": "analyst"
        }
    """
    api_key = os.environ.get("AIML_API_KEY", "")
    if not api_key:
        return _error_response("AIML_API_KEY not set in environment")

    # Sanitize all user-supplied inputs
    safe_diff = sanitize_input(diff)
    safe_title = sanitize_input(pr_title)
    safe_description = sanitize_input(pr_description)

    style_context = ""
    if style_profile and style_profile.get("summary"):
        style_context = f"\n\nTeam style context:\n{style_profile['summary']}"

    system_prompt = """You are a senior software architect analyzing a pull request.
Your job is to understand WHAT the developer was trying to accomplish and WHY.
Be precise, technical, and honest. Do not flatter bad code.
Respond ONLY with valid JSON matching this exact schema — no markdown, no preamble:
{
  "summary": "string",
  "intent": "string",
  "key_changes": ["string"],
  "complexity": "low|medium|high",
  "risk_areas": ["string"]
}"""

    user_message = f"""PR Title: {safe_title}
PR Description: {safe_description}{style_context}

Diff:
{safe_diff}"""

    try:
        response = requests.post(
            AIML_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 1000,
                "temperature": 0.2,  # Low temp for consistent structured output
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if model adds them anyway
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["agent"] = "analyst"
        return result

    except requests.exceptions.HTTPError as e:
        return _error_response(f"AI/ML API HTTP error: {e.response.status_code}")
    except requests.exceptions.Timeout:
        return _error_response("AI/ML API timed out")
    except json.JSONDecodeError as e:
        return _error_response(f"Could not parse analyst response: {e}")
    except Exception as e:
        return _error_response(f"Analyst agent error: {str(e)}")


def _error_response(message: str) -> dict:
    return {
        "summary": f"Analysis unavailable: {message}",
        "intent": "Unknown",
        "key_changes": [],
        "complexity": "unknown",
        "risk_areas": [],
        "agent": "analyst",
        "error": message,
    }
