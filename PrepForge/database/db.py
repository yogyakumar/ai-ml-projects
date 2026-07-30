"""
database/db.py
Single place that owns the SQLite connection, schema, and all read/write
helpers. Every page imports from here instead of touching sqlite3 directly.
"""

import sqlite3
import hashlib
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mission_os.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            placement_target_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dsa_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lecture_no TEXT,
            topic TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            difficulty TEXT DEFAULT 'Medium',
            date_done TEXT,
            time_spent_min INTEGER DEFAULT 0,
            notes TEXT,
            revision1_date TEXT,
            revision2_date TEXT,
            revision3_date TEXT,
            revision1_done INTEGER DEFAULT 0,
            revision2_done INTEGER DEFAULT 0,
            revision3_done INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            topic TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            notes TEXT,
            date_done TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            wake_up INTEGER DEFAULT 0,
            workout INTEGER DEFAULT 0,
            meditation INTEGER DEFAULT 0,
            reading INTEGER DEFAULT 0,
            coding INTEGER DEFAULT 0,
            revision INTEGER DEFAULT 0,
            no_social_media INTEGER DEFAULT 0,
            water INTEGER DEFAULT 0,
            sleep INTEGER DEFAULT 0,
            UNIQUE(user_id, log_date),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS placement_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            UNIQUE(user_id, item),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT,
            github_link TEXT,
            demo_link TEXT,
            deployed INTEGER DEFAULT 0,
            linkedin_post INTEGER DEFAULT 0,
            resume_ready INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            tags TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

    init_question_bank_table()
    init_resume_portfolio_tables()


# ---------------- AUTH ----------------

def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str, placement_date: str = None):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, placement_target_date) VALUES (?, ?, ?)",
            (username, _hash_pw(password), placement_date),
        )
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def verify_user(username: str, password: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row and row["password_hash"] == _hash_pw(password):
        return dict(row)
    return None


# ---------------- DSA TRACKER ----------------

def add_dsa_entry(user_id, lecture_no, topic, status, difficulty, time_spent_min, notes):
    conn = get_conn()
    today = date.today().isoformat()
    rev1 = rev2 = rev3 = None
    # Adaptive scheduling: harder topics get closer, more frequent revision
    if status == "Completed":
        gaps = {"Hard": (1, 3, 7), "Medium": (3, 7, 15), "Easy": (7, 15, 30)}
        g1, g2, g3 = gaps.get(difficulty, (3, 7, 15))
        rev1 = (date.today() + timedelta(days=g1)).isoformat()
        rev2 = (date.today() + timedelta(days=g2)).isoformat()
        rev3 = (date.today() + timedelta(days=g3)).isoformat()

    conn.execute(
        """INSERT INTO dsa_progress
           (user_id, lecture_no, topic, status, difficulty, date_done, time_spent_min,
            notes, revision1_date, revision2_date, revision3_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, lecture_no, topic, status, difficulty,
         today if status == "Completed" else None, time_spent_min, notes, rev1, rev2, rev3),
    )
    conn.commit()
    conn.close()


def get_dsa_entries(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM dsa_progress WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_dsa_status(entry_id, status, difficulty):
    """Used when a Pending entry is marked Completed later; (re)schedules revisions."""
    conn = get_conn()
    today = date.today().isoformat()
    gaps = {"Hard": (1, 3, 7), "Medium": (3, 7, 15), "Easy": (7, 15, 30)}
    g1, g2, g3 = gaps.get(difficulty, (3, 7, 15))
    rev1 = (date.today() + timedelta(days=g1)).isoformat()
    rev2 = (date.today() + timedelta(days=g2)).isoformat()
    rev3 = (date.today() + timedelta(days=g3)).isoformat()
    conn.execute(
        """UPDATE dsa_progress SET status=?, difficulty=?, date_done=?,
           revision1_date=?, revision2_date=?, revision3_date=? WHERE id=?""",
        (status, difficulty, today, rev1, rev2, rev3, entry_id),
    )
    conn.commit()
    conn.close()


def mark_revision_done(entry_id, which: int):
    conn = get_conn()
    conn.execute(f"UPDATE dsa_progress SET revision{which}_done = 1 WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def get_due_revisions(user_id):
    """Revisions whose date is today or earlier and not yet marked done."""
    entries = get_dsa_entries(user_id)
    today = date.today().isoformat()
    due = []
    for e in entries:
        for i in (1, 2, 3):
            rdate = e.get(f"revision{i}_date")
            rdone = e.get(f"revision{i}_done")
            if rdate and rdate <= today and not rdone:
                due.append({"topic": e["topic"], "which": i, "date": rdate, "id": e["id"]})
    return due


# ---------------- AI TRACKER ----------------

AI_DEFAULT_TOPICS = {
    "Deep Learning": ["CNN", "RNN", "LSTM", "GAN", "Transformers", "Attention", "BERT", "GPT", "LLM"],
    "GenAI & Prompting": ["Prompt Engineering", "Fine Tuning", "LoRA", "QLoRA", "RAG", "Vector DB", "Embeddings"],
    "Agentic AI": ["LangChain", "LangGraph", "CrewAI", "AutoGen", "MCP"],
    "MLOps / Deployment": ["FastAPI", "MLflow", "Docker", "Kubernetes", "CI/CD", "AWS", "Azure", "GCP",
                            "Monitoring", "Evaluation", "AI Security"],
    "Inference Optimization": ["vLLM", "ONNX", "TensorRT Basics"],
}


def seed_ai_topics(user_id):
    conn = get_conn()
    existing = conn.execute("SELECT COUNT(*) c FROM ai_progress WHERE user_id=?", (user_id,)).fetchone()["c"]
    if existing == 0:
        for module, topics in AI_DEFAULT_TOPICS.items():
            for t in topics:
                conn.execute(
                    "INSERT INTO ai_progress (user_id, module, topic) VALUES (?, ?, ?)",
                    (user_id, module, t),
                )
        conn.commit()
    conn.close()


def get_ai_progress(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ai_progress WHERE user_id=? ORDER BY module, id", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_ai_topic(topic_id, done: bool):
    conn = get_conn()
    conn.execute(
        "UPDATE ai_progress SET done=?, date_done=? WHERE id=?",
        (1 if done else 0, date.today().isoformat() if done else None, topic_id),
    )
    conn.commit()
    conn.close()


# ---------------- PLACEMENT CHECKLIST ----------------

PLACEMENT_ITEMS = {
    "Core Subjects": ["OOP", "DBMS", "SQL", "OS", "CN"],
    "Soft Skills": ["Aptitude", "Communication", "Mock Interviews"],
    "Profile": ["Resume", "LinkedIn", "Github", "Portfolio"],
}


def seed_placement_checklist(user_id):
    conn = get_conn()
    existing = conn.execute(
        "SELECT COUNT(*) c FROM placement_checklist WHERE user_id=?", (user_id,)
    ).fetchone()["c"]
    if existing == 0:
        for cat, items in PLACEMENT_ITEMS.items():
            for item in items:
                conn.execute(
                    "INSERT INTO placement_checklist (user_id, item, category) VALUES (?, ?, ?)",
                    (user_id, item, cat),
                )
        conn.commit()
    conn.close()


def get_placement_checklist(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM placement_checklist WHERE user_id=? ORDER BY category, id", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_placement_item(item_id, done: bool):
    conn = get_conn()
    conn.execute("UPDATE placement_checklist SET done=? WHERE id=?", (1 if done else 0, item_id))
    conn.commit()
    conn.close()


# ---------------- HABITS ----------------

HABIT_COLUMNS = ["wake_up", "workout", "meditation", "reading", "coding",
                  "revision", "no_social_media", "water", "sleep"]


def get_or_create_today_habit(user_id):
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT * FROM habits WHERE user_id=? AND log_date=?", (user_id, today)
    ).fetchone()
    if not row:
        conn.execute("INSERT INTO habits (user_id, log_date) VALUES (?, ?)", (user_id, today))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM habits WHERE user_id=? AND log_date=?", (user_id, today)
        ).fetchone()
    conn.close()
    return dict(row)


def update_habit(user_id, log_date, column, value: bool):
    conn = get_conn()
    conn.execute(
        f"UPDATE habits SET {column}=? WHERE user_id=? AND log_date=?",
        (1 if value else 0, user_id, log_date),
    )
    conn.commit()
    conn.close()


def get_habit_history(user_id, days=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM habits WHERE user_id=? ORDER BY log_date DESC LIMIT ?",
        (user_id, days),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def current_streak(user_id, column="coding"):
    history = get_habit_history(user_id, days=365)
    history_by_date = {h["log_date"]: h for h in history}
    streak = 0
    d = date.today()
    while True:
        h = history_by_date.get(d.isoformat())
        if h and h.get(column):
            streak += 1
            d -= timedelta(days=1)
        else:
            break
    return streak


# ---------------- OVERALL PROGRESS (for Dashboard) ----------------

def overall_progress_pct(user_id):
    dsa = get_dsa_entries(user_id)
    ai = get_ai_progress(user_id)
    placement = get_placement_checklist(user_id)

    total = len(dsa) + len(ai) + len(placement)
    if total == 0:
        return 0
    done = (
        sum(1 for d in dsa if d["status"] == "Completed")
        + sum(1 for a in ai if a["done"])
        + sum(1 for p in placement if p["done"])
    )
    return round((done / total) * 100, 1)


# ---------------- NOTES (Module 11) ----------------

def add_note(user_id, title, content, tags):
    conn = get_conn()
    conn.execute(
        "INSERT INTO notes (user_id, title, content, tags) VALUES (?, ?, ?, ?)",
        (user_id, title, content, tags),
    )
    conn.commit()
    conn.close()


def get_notes(user_id, search: str = "", tag: str = ""):
    conn = get_conn()
    query = "SELECT * FROM notes WHERE user_id=?"
    params = [user_id]
    if search:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if tag:
        query += " AND tags LIKE ?"
        params += [f"%{tag}%"]
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_note(note_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


def all_note_tags(user_id):
    notes = get_notes(user_id)
    tags = set()
    for n in notes:
        if n["tags"]:
            tags.update(t.strip() for t in n["tags"].split(",") if t.strip())
    return sorted(tags)


# ---------------- QUESTION BANK (Module 12) ----------------

def init_question_bank_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS question_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            platform TEXT,
            topic TEXT,
            difficulty TEXT DEFAULT 'Medium',
            company TEXT,
            status TEXT DEFAULT 'Not Attempted',
            link TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def add_question(user_id, question, platform, topic, difficulty, company, link):
    conn = get_conn()
    conn.execute(
        """INSERT INTO question_bank (user_id, question, platform, topic, difficulty, company, link)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, question, platform, topic, difficulty, company, link),
    )
    conn.commit()
    conn.close()


def get_questions(user_id, platform=None, topic=None, difficulty=None, company=None):
    conn = get_conn()
    query = "SELECT * FROM question_bank WHERE user_id=?"
    params = [user_id]
    for col, val in [("platform", platform), ("topic", topic), ("difficulty", difficulty), ("company", company)]:
        if val and val != "All":
            query += f" AND {col}=?"
            params.append(val)
    query += " ORDER BY id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_question_status(qid, status):
    conn = get_conn()
    conn.execute("UPDATE question_bank SET status=? WHERE id=?", (status, qid))
    conn.commit()
    conn.close()


def distinct_values(user_id, column):
    conn = get_conn()
    rows = conn.execute(
        f"SELECT DISTINCT {column} FROM question_bank WHERE user_id=? AND {column} IS NOT NULL AND {column}!=''",
        (user_id,),
    ).fetchall()
    conn.close()
    return sorted(r[0] for r in rows)


# ---------------- RESUME / PORTFOLIO TRACKER (Modules 13-14) ----------------

def init_resume_portfolio_tables():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resume_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            UNIQUE(user_id, item),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT,
            date_added TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


RESUME_ITEMS = {
    "Content": ["Skills section up to date", "Projects have measurable impact",
                "Missing-skills gap identified", "Tailored for target role"],
    "Interview Readiness": ["Can explain every project in depth", "STAR-format stories ready",
                             "Mock interview done", "Common HR questions prepped"],
}


def seed_resume_checklist(user_id):
    conn = get_conn()
    existing = conn.execute(
        "SELECT COUNT(*) c FROM resume_checklist WHERE user_id=?", (user_id,)
    ).fetchone()["c"]
    if existing == 0:
        for cat, items in RESUME_ITEMS.items():
            for item in items:
                conn.execute(
                    "INSERT INTO resume_checklist (user_id, item, category) VALUES (?, ?, ?)",
                    (user_id, item, cat),
                )
        conn.commit()
    conn.close()


def get_resume_checklist(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM resume_checklist WHERE user_id=? ORDER BY category, id", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_resume_item(item_id, done: bool):
    conn = get_conn()
    conn.execute("UPDATE resume_checklist SET done=? WHERE id=?", (1 if done else 0, item_id))
    conn.commit()
    conn.close()


def resume_score(user_id):
    items = get_resume_checklist(user_id)
    if not items:
        return 0
    return round(sum(i["done"] for i in items) / len(items) * 100, 1)


def add_portfolio_item(user_id, item_type, title, link):
    conn = get_conn()
    conn.execute(
        "INSERT INTO portfolio_items (user_id, item_type, title, link) VALUES (?, ?, ?, ?)",
        (user_id, item_type, title, link),
    )
    conn.commit()
    conn.close()


def get_portfolio_items(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM portfolio_items WHERE user_id=? ORDER BY date_added DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_portfolio_item(item_id):
    conn = get_conn()
    conn.execute("DELETE FROM portfolio_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ---------------- CALENDAR (Module 7) ----------------

def calendar_day_view(user_id, day_iso: str):
    """Everything relevant to one date: what's due for revision, what was completed."""
    conn = get_conn()
    completed = conn.execute(
        "SELECT topic, 'DSA' as source FROM dsa_progress WHERE user_id=? AND date_done=?"
        " UNION ALL "
        "SELECT topic, 'AI' as source FROM ai_progress WHERE user_id=? AND date_done=?",
        (user_id, day_iso, user_id, day_iso),
    ).fetchall()
    revisions_due = conn.execute(
        """SELECT topic, revision1_date as rd, 1 as which FROM dsa_progress
           WHERE user_id=? AND revision1_date=? AND revision1_done=0
           UNION ALL
           SELECT topic, revision2_date as rd, 2 as which FROM dsa_progress
           WHERE user_id=? AND revision2_date=? AND revision2_done=0
           UNION ALL
           SELECT topic, revision3_date as rd, 3 as which FROM dsa_progress
           WHERE user_id=? AND revision3_date=? AND revision3_done=0""",
        (user_id, day_iso, user_id, day_iso, user_id, day_iso),
    ).fetchall()
    conn.close()
    return {
        "completed": [dict(r) for r in completed],
        "revisions_due": [dict(r) for r in revisions_due],
    }


def month_activity_counts(user_id, year: int, month: int):
    """Returns {day_number: activity_count} for a given month, for a simple calendar heat view."""
    conn = get_conn()
    prefix = f"{year:04d}-{month:02d}-"
    rows = conn.execute(
        "SELECT date_done as d FROM dsa_progress WHERE user_id=? AND date_done LIKE ?"
        " UNION ALL "
        "SELECT date_done as d FROM ai_progress WHERE user_id=? AND date_done LIKE ?",
        (user_id, f"{prefix}%", user_id, f"{prefix}%"),
    ).fetchall()
    conn.close()
    counts = {}
    for r in rows:
        day = int(r["d"].split("-")[2])
        counts[day] = counts.get(day, 0) + 1
    return counts


def get_weak_topics(user_id, limit=10):
    """Hard-difficulty topics, most recent first — used as 'weak areas' context for the AI Mentor."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT topic, status, date_done FROM dsa_progress WHERE user_id=? AND difficulty='Hard' "
        "ORDER BY id DESC LIMIT ?", (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------- ANALYTICS / WEEKLY REPORT (Module 8) ----------------

def weekly_report(user_id):
    from datetime import date, timedelta
    conn = get_conn()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    dsa_done = conn.execute(
        "SELECT topic, difficulty, time_spent_min, date_done FROM dsa_progress "
        "WHERE user_id=? AND date_done >= ?", (user_id, week_ago),
    ).fetchall()
    ai_done = conn.execute(
        "SELECT topic, module FROM ai_progress WHERE user_id=? AND date_done >= ?",
        (user_id, week_ago),
    ).fetchall()
    pending_dsa = conn.execute(
        "SELECT COUNT(*) c FROM dsa_progress WHERE user_id=? AND status != 'Completed'", (user_id,)
    ).fetchone()["c"]
    habits = conn.execute(
        "SELECT * FROM habits WHERE user_id=? AND log_date >= ?", (user_id, week_ago)
    ).fetchall()
    conn.close()

    total_hours = round(sum(r["time_spent_min"] for r in dsa_done) / 60, 1)
    habit_consistency = 0
    if habits:
        total_checks = sum(sum(h[c] for c in HABIT_COLUMNS) for h in habits)
        habit_consistency = round(total_checks / (len(habits) * len(HABIT_COLUMNS)) * 100, 1)

    return {
        "topics_completed": len(dsa_done) + len(ai_done),
        "dsa_completed": [dict(r) for r in dsa_done],
        "ai_completed": [dict(r) for r in ai_done],
        "pending_topics": pending_dsa,
        "hours_studied": total_hours,
        "habit_consistency_pct": habit_consistency,
    }
