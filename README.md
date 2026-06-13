PR Shield - Multi-Agent AI Code Review System
Band of Agents Hackathon 2026 | AI/ML API x Featherless AI x Band SDK
PR Shield does not just review code. It learns your team coding style and reviews PRs the way YOUR specific senior developer would. Not generic AI feedback. YOUR teams feedback.
The Problem
Every developer knows the pain. You submit a PR and get back generic AI feedback that could apply to any codebase anywhere. It does not know your teams conventions, what your senior developer cares about, or the context behind your changes. Generic AI reviews are noise not signal. Bad reviews cost companies millions in security breaches and technical debt every year.
The Solution
Three specialized AI agents coordinated through Band review every PR from every angle. The Analyst understands what you were trying to do. The Security agent catches what could go wrong. The Mentor writes feedback that sounds like it came from the person who knows your codebase best because it learned from them.
Three Agents Coordinated Through Band
Analyst Agent powered by AI/ML API understands PR intent maps changes to goals identifies complexity and flags risk areas before the other agents even start.
Security Agent powered by Featherless AI scans for SQL injection XSS hardcoded secrets insecure hashing authentication flaws and runs a static pattern scan before AI analysis so nothing gets missed.
Mentor Agent powered by AI/ML API synthesizes both agents findings and writes personalized feedback in your teams voice using the Style Memory engine.
Style Memory - The Winning Twist
Feed PR Shield examples of your teams merged PRs and the reviews they received. It builds a reviewer persona learning your naming conventions what your senior developer pushes back on and how your team actually communicates. Every review then says Reviewed as Alex Chen. That is not generic AI feedback. That is YOUR teams feedback. This is impossible without multi-agent AI.
How Band Coordinates the Agents
When a PR is submitted Band coordinates the agents in sequence. The Analyst agent analyzes intent and complexity using AI/ML API. The Security agent scans for vulnerabilities using Featherless AI. The Mentor agent synthesizes everything and writes the final review. Each agent hands off structured context to the next through Band making this a genuine multi-agent workflow not a thin wrapper.
Security Built In
All API keys are stored in environment variables and never appear in code. Every input is sanitized using bleach before reaching any agent. Rate limiting prevents abuse with maximum 10 reviews per minute. SQL injection is prevented through parameterized queries. Security headers are added to every response. A static secret scanner runs on every diff before AI analysis catches hardcoded passwords API keys and private keys instantly.
Quick Start
Clone the repository and install dependencies using pip install -r requirements.txt then copy .env.example to .env and fill in your API keys then run python core/init_db.py to initialize the database then run python app.py and open localhost:5000 in your browser.
Tech Stack
Python 3.12 and Flask for the backend. Band SDK as the multi-agent coordination layer. AI/ML API powering the Analyst and Mentor agents. Featherless AI powering the Security agent. SQLite for Style Memory storage. Vanilla JavaScript and CSS for the professional UI.
What Makes This Different
Every other team built an AI code reviewer. PR Shield builds YOUR code reviewer. It learns from your history gets better over time and sounds like the senior developer your team actually has. That is genuinely new and genuinely useful beyond the hackathon.
Hackathon
Band of Agents Hackathon 2026 built on lablab.ai from June 12 to June 19. 