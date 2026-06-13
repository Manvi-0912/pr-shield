# 🛡️ PR Shield — Multi-Agent AI Code Review System
### Band of Agents Hackathon 2026 Entry

> PR Shield doesn't just review code — it learns your team's coding style and reviews PRs the way YOUR senior developer would.

## Three Agents
| Agent | Provider | Role |
|-------|----------|------|
| Analyst | AI/ML API | Understands PR intent, maps changes to goals |
| Security | Featherless AI | Scans for vulnerabilities, injection attacks, secrets |
| Mentor | Google Gemini | Writes senior-dev feedback in YOUR team's voice |

## Quick Start (Windows, VS Code, Python 3.12)

### 1. Create virtual environment
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set API keys
```bash
copy .env.example .env
# Fill in your keys in .env
```

### 3. Initialize and run
```bash
python core/init_db.py
python app.py
# Visit http://localhost:5000
```

## Promo Codes
- AI/ML API: BANDHACK26 at aimlapi.com
- Featherless AI: BOA26 at featherless.ai
