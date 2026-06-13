import os
import json
import bleach
import requests
from typing import Optional

AIML_API_URL = "https://api.aimlapi.com/chat/completions"

def sanitize_input(text: str) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned[:50_000]

def write_review(diff, analyst_result, security_result, style_profile=None):
    api_key = os.environ.get("AIML_API_KEY", "")
    if not api_key:
        return _error_response("AIML_API_KEY not set")

    safe_diff = sanitize_input(diff)
    persona_block = _build_persona(style_profile)
    analyst_summary = analyst_result.get("summary", "No analysis")
    analyst_intent = analyst_result.get("intent", "Unknown")
    security_risk = security_result.get("overall_risk", "review")
    vulnerabilities = security_result.get("vulnerabilities", [])
    critical_vulns = [v for v in vulnerabilities if v.get("severity") in ("critical", "high")]

    prompt = f"""You are doing a code review. {persona_block}

CONTEXT FROM OTHER AGENTS:
- Intent: {analyst_intent}
- Summary: {analyst_summary}
- Security risk level: {security_risk}
- Critical security issues found: {len(critical_vulns)}
{f"- Issues: {[v['description'] for v in critical_vulns]}" if critical_vulns else ""}

PR DIFF:
{safe_diff}

Write an honest, specific code review. Praise good work, push back on bad decisions.

Respond ONLY with valid JSON — no markdown, no preamble:
{{
  "overall_verdict": "approve|request_changes|needs_discussion",
  "tone_used": "string",
  "inline_comments": [
    {{
      "location": "string",
      "type": "suggestion|praise|concern|nit",
      "comment": "string"
    }}
  ],
  "summary_feedback": "string",
  "what_was_done_well": ["string"],
  "required_changes": ["string"],
  "optional_improvements": ["string"]
}}"""

    try:
        response = requests.post(
            AIML_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.4,
            },
            timeout=30,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["agent"] = "mentor"
        return result

    except Exception as e:
        return _error_response(str(e))


def _build_persona(style_profile):
    if not style_profile:
        return "You are a thoughtful, experienced senior developer. Be direct and constructive."
    name = style_profile.get("reviewer_name", "Senior Dev")
    style = style_profile.get("communication_style", "direct")
    values = style_profile.get("values", ["clean code", "tests"])
    pet_peeves = style_profile.get("pet_peeves", [])
    phrases = style_profile.get("sample_phrases", [])
    persona = f"You are {name}, a senior developer. Style: {style}. "
    persona += f"You value: {', '.join(values)}. "
    if pet_peeves:
        persona += f"You always flag: {', '.join(pet_peeves)}. "
    if phrases:
        persona += f"Phrases you use: {'; '.join(phrases[:3])}."
    return persona


def _error_response(message):
    return {
        "overall_verdict": "needs_discussion",
        "tone_used": "Default",
        "inline_comments": [],
        "summary_feedback": f"Review unavailable: {message}",
        "what_was_done_well": [],
        "required_changes": [],
        "optional_improvements": [],
        "agent": "mentor",
        "error": message,
    }