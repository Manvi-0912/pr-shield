"""
Security Agent — powered by Featherless AI
Role: Scan for security vulnerabilities, exposed secrets,
      injection risks, and insecure patterns.
Uses a security-focused model via Featherless AI's OpenAI-compatible API.
"""

import os
import json
import re
import requests
import bleach
from typing import Optional


FEATHERLESS_API_URL = "https://api.featherless.ai/v1/chat/completions"
# Security-focused model — good at code analysis
MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"


# Patterns that suggest hard-coded secrets — caught BEFORE sending to AI
# This is a fast local pre-scan, not a replacement for AI analysis
HARDCODED_SECRET_PATTERNS = [
    (r'(?i)(api_key|apikey|secret|password|passwd|token|auth)\s*=\s*["\'][^"\']{8,}["\']', "Possible hardcoded secret"),
    (r'(?i)Bearer\s+[A-Za-z0-9\-_]{20,}', "Possible hardcoded Bearer token"),
    (r'(?i)sk-[A-Za-z0-9]{20,}', "Possible OpenAI-style API key"),
    (r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----', "Private key in code"),
]


def sanitize_input(text: str) -> str:
    cleaned = bleach.clean(text, tags=[], strip=True)
    return cleaned[:50_000]


def local_secret_scan(diff: str) -> list[dict]:
    """Fast regex pre-scan before sending to AI. Returns found issues."""
    findings = []
    for pattern, label in HARDCODED_SECRET_PATTERNS:
        matches = re.findall(pattern, diff)
        if matches:
            findings.append({
                "type": "hardcoded_secret",
                "label": label,
                "severity": "critical",
                "note": "Found by static pattern scan before AI analysis"
            })
    return findings


def scan_security(
    diff: str,
    analyst_context: Optional[dict] = None,
) -> dict:
    """
    Scan a PR diff for security vulnerabilities.

    Returns:
        {
            "vulnerabilities": [
                {
                    "severity": "critical|high|medium|low|info",
                    "type": str,
                    "location": str,
                    "description": str,
                    "recommendation": str
                }
            ],
            "secret_scan": list,      # From local pattern scan
            "overall_risk": str,      # "pass|review|block"
            "agent": "security"
        }
    """
    api_key = os.environ.get("FEATHERLESS_API_KEY", "")
    if not api_key:
        return _error_response("FEATHERLESS_API_KEY not set in environment")

    safe_diff = sanitize_input(diff)

    # Always run local scan first — fast and catches obvious issues
    secret_findings = local_secret_scan(safe_diff)

    # Build context from analyst if available
    risk_context = ""
    if analyst_context and analyst_context.get("risk_areas"):
        areas = ", ".join(analyst_context["risk_areas"])
        risk_context = f"\n\nAnalyst flagged these risk areas: {areas}"

    system_prompt = """You are a security engineer doing a code review security audit.
Scan the PR diff for:
- SQL injection, XSS, command injection, path traversal
- Authentication/authorization flaws
- Insecure data handling (logging secrets, weak crypto)
- Dependency risks
- Race conditions or TOCTOU issues
- Any code that trusts user input without validation

Be specific. Point to the actual code. Don't flag theoretical risks without evidence.
Respond ONLY with valid JSON — no markdown, no preamble:
{
  "vulnerabilities": [
    {
      "severity": "critical|high|medium|low|info",
      "type": "string",
      "location": "string (file:line or function name)",
      "description": "string",
      "recommendation": "string"
    }
  ],
  "overall_risk": "pass|review|block"
}
If no issues found, return empty vulnerabilities array and overall_risk "pass"."""

    user_message = f"""Review this diff for security vulnerabilities:{risk_context}

{safe_diff}"""

    try:
        response = requests.post(
            FEATHERLESS_API_URL,
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
                "max_tokens": 1200,
                "temperature": 0.1,  # Very low — security analysis needs consistency
            },
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["secret_scan"] = secret_findings
        result["agent"] = "security"

        # Escalate overall_risk if local scan found secrets
        if secret_findings and result.get("overall_risk") != "block":
            result["overall_risk"] = "block"

        return result

    except requests.exceptions.HTTPError as e:
        return _error_response(f"Featherless API HTTP error: {e.response.status_code}")
    except requests.exceptions.Timeout:
        return _error_response("Featherless API timed out")
    except json.JSONDecodeError as e:
        return _error_response(f"Could not parse security response: {e}")
    except Exception as e:
        return _error_response(f"Security agent error: {str(e)}")


def _error_response(message: str) -> dict:
    return {
        "vulnerabilities": [],
        "secret_scan": [],
        "overall_risk": "review",
        "agent": "security",
        "error": message,
    }
