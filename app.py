"""
PR Shield — Flask Application
Full security: rate limiting, input validation, no exposed keys.
"""

import os
import secrets
from flask import Flask, request, jsonify, render_template, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import bleach

load_dotenv()  # Load .env file — all keys stay server-side

from band_agents import run_review_sync as run_review
from core.style_memory import save_style_sample, get_style_profile, get_sample_count
from core.init_db import init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

# Rate limiting — prevents abuse
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Initialize DB on startup
init_db()


# ─── Security Headers ────────────────────────────────────────────────────────

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:;"
    )
    return response


# ─── Input Validation ────────────────────────────────────────────────────────

def validate_and_clean(data: dict) -> tuple[dict, str | None]:
    """Validate and sanitize incoming review request. Returns (clean_data, error)."""
    diff = data.get("diff", "").strip()
    title = data.get("pr_title", "").strip()
    description = data.get("pr_description", "").strip()
    team_id = data.get("team_id", "default").strip()

    if not diff:
        return {}, "diff is required"
    if len(diff) > 100_000:
        return {}, "diff exceeds 100,000 character limit"
    if not title:
        return {}, "pr_title is required"
    if len(title) > 500:
        return {}, "pr_title too long"
    if len(description) > 5000:
        return {}, "pr_description too long"

    # Allow only alphanumeric + dash/underscore for team_id
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]{1,64}$', team_id):
        team_id = "default"

    return {
        "diff": bleach.clean(diff, tags=[], strip=True),
        "pr_title": bleach.clean(title, tags=[], strip=True),
        "pr_description": bleach.clean(description, tags=[], strip=True),
        "team_id": team_id,
    }, None


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/review", methods=["POST"])
@limiter.limit("10 per minute")
def api_review():
    """Main review endpoint. Runs all three agents."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    clean, error = validate_and_clean(data)
    if error:
        return jsonify({"error": error}), 422

    try:
        result = run_review(
            diff=clean["diff"],
            pr_title=clean["pr_title"],
            pr_description=clean["pr_description"],
            team_id=clean["team_id"],
        )
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Review failed: {e}")
        return jsonify({"error": "Review failed. Please try again."}), 500


@app.route("/api/style/add", methods=["POST"])
@limiter.limit("20 per hour")
def api_add_style_sample():
    """Add a merged PR as a style training sample."""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    team_id_raw = data.get("team_id", "default")

    import re
    team_id = team_id_raw if re.match(r'^[a-zA-Z0-9_\-]{1,64}$', team_id_raw) else "default"
    diff = bleach.clean(data.get("diff", ""), tags=[], strip=True)[:30_000]
    review = bleach.clean(data.get("review_text", ""), tags=[], strip=True)[:5_000]
    reviewer = bleach.clean(data.get("reviewer_name", "Senior Dev"), tags=[], strip=True)[:128]

    if not diff or not review:
        return jsonify({"error": "diff and review_text are required"}), 422

    ok = save_style_sample(team_id, diff, review, reviewer)
    if ok:
        count = get_sample_count(team_id)
        return jsonify({
            "success": True,
            "sample_count": count,
            "message": f"Style sample saved. Profile will update with {count} sample(s)."
        })
    return jsonify({"error": "Failed to save style sample"}), 500


@app.route("/api/style/profile/<team_id>")
@limiter.limit("30 per minute")
def api_get_profile(team_id):
    """Get the current style profile for a team."""
    import re
    if not re.match(r'^[a-zA-Z0-9_\-]{1,64}$', team_id):
        abort(400)

    profile = get_style_profile(team_id)
    count = get_sample_count(team_id)
    if profile:
        return jsonify({"profile": profile, "sample_count": count})
    return jsonify({"profile": None, "sample_count": count})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="127.0.0.1", port=5000)
