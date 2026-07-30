# AI-Mission-OS

A personal placement + AI/ML prep command center — built with Streamlit + SQLite.

Built and tested so far:

- ✅ Module 1 — Dashboard (progress, streak, countdown, today's mission, revisions due)
- ✅ Module 2 — DSA Tracker (log topics, difficulty, adaptive revision scheduling, charts)
- ✅ Module 3 — AI Tracker (Deep Learning → GenAI → Agentic AI → MLOps checklist, pre-seeded)
- ✅ Module 5 — Placement Tracker (OOP/DBMS/SQL/OS/CN + soft skills + profile checklist)
- ✅ Module 6 — Habit Tracker (daily habits, streaks, 30-day consistency chart)
- ✅ Module 11 — Notes (Markdown notes, tags, search)
- ✅ Module 12 — Question Bank (LeetCode/GFG/CodeStudio, topic/difficulty/company filters, status tracking)
- ✅ Module 13/14 — Resume & Portfolio Tracker (resume score, portfolio item log)
- ✅ Module 7 — Calendar (monthly activity view + day-detail lookup)
- ✅ Module 8 — Analytics + weekly report (readiness radar, Excel & PDF export)
- ✅ Module 10 — AI Mentor chatbot (Google Gemini, free tier)
- ✅ Basic multi-user auth (signup/login, each user's data is isolated)

## Setting up the AI Mentor (Gemini)

1. Get a free key at **aistudio.google.com** → API Keys.
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
3. Paste your key in: `GEMINI_API_KEY = "your-key-here"`.
4. `.streamlit/secrets.toml` is already in `.gitignore` — it will never be pushed to GitHub.

**Never paste your API key directly into any `.py` file** — especially since this repo needs to
be public for free Streamlit deployment. If a key is ever accidentally exposed (posted publicly,
committed to git, etc.), regenerate it immediately from the same AI Studio page.

## Not built yet (v2 roadmap)

- Module 9 automatic *outside-the-app* reminders (email/push — in-app "due today" already works)
- Note image/PDF file uploads (currently link-based)
- Dark/Light theme toggle, custom roadmaps per user

## Deploying for free

Streamlit Community Cloud (share.streamlit.io) is free: push this repo to a **public** GitHub repo
(add `mission_os.db` to `.gitignore` first — don't commit real user data), connect the repo on
share.streamlit.io, and deploy. Limits: ~1 GB RAM, app sleeps after inactivity, and SQLite data may
not persist reliably across redeploys — fine for a portfolio demo, but for a real multi-user launch
later, move to a hosted Postgres (e.g. Supabase's free tier).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

First run creates `mission_os.db` automatically. Sign up, then use the sidebar
to move between Dashboard / DSA Tracker / AI Tracker / Placement Tracker / Habit Tracker.
