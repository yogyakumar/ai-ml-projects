"""
app.py — AI-Mission-OS entry point.
Handles auth (login / signup) then shows the Dashboard.
Other modules live in pages/ and are auto-discovered by Streamlit's
multipage navigation once a user is logged in.
"""

import random
from datetime import date

import streamlit as st

from database import db

st.set_page_config(page_title="AI-Mission-OS", page_icon="🚀", layout="wide")
db.init_db()

QUOTES = [
    "Discipline beats motivation. Show up anyway.",
    "One zip a day gets you further than one binge a month.",
    "The DSA sheet doesn't care about your mood. Neither should you.",
    "Every 'Hard' topic today is an 'Easy' revision in 7 days.",
    "You're not behind. You're exactly on day N of your own plan.",
    "Consistency compounds. So does neglect.",
]


def login_signup_screen():
    st.title("🚀 AI-Mission-OS")
    st.caption("Your placement + AI/ML prep command center")

    tab_login, tab_signup = st.tabs(["Login", "Create account"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            user = db.verify_user(u, p)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_signup:
        with st.form("signup_form"):
            u = st.text_input("Choose a username")
            p = st.text_input("Choose a password", type="password")
            target = st.date_input("Placement target date (optional)", value=None)
            submitted = st.form_submit_button("Create account")
        if submitted:
            ok, msg = db.create_user(u, p, target.isoformat() if target else None)
            if ok:
                st.success(f"{msg} You can log in now.")
            else:
                st.error(msg)


def dashboard():
    user = st.session_state["user"]
    st.sidebar.success(f"Logged in as {user['username']}")
    if st.sidebar.button("Log out"):
        del st.session_state["user"]
        st.rerun()

    db.seed_ai_topics(user["id"])
    db.seed_placement_checklist(user["id"])

    st.title("📊 Dashboard")
    st.caption(f"Today's Quote: _{random.choice(QUOTES)}_")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Overall Progress", f"{db.overall_progress_pct(user['id'])}%")

    with col2:
        streak = db.current_streak(user["id"], "coding")
        st.metric("Coding Streak", f"{streak} 🔥")

    with col3:
        if user.get("placement_target_date"):
            days_left = (date.fromisoformat(user["placement_target_date"]) - date.today()).days
            st.metric("Countdown to Placement", f"{max(days_left, 0)} days")
        else:
            st.metric("Countdown to Placement", "Not set")

    with col4:
        due = db.get_due_revisions(user["id"])
        st.metric("Revisions Due Today", len(due))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Today's Mission")
        dsa = db.get_dsa_entries(user["id"])
        pending = [d for d in dsa if d["status"] != "Completed"]
        if pending:
            for p in pending[:5]:
                st.write(f"- 🔲 {p['topic']} ({p['difficulty']})")
        else:
            st.write("No pending DSA topics — log one in the DSA Tracker.")

    with right:
        st.subheader("Revisions Due")
        if due:
            for d in due:
                st.write(f"- 🔁 {d['topic']} (Revision {d['which']}, was due {d['date']})")
        else:
            st.write("Nothing due today. 🎉")

    st.divider()
    st.info("Use the sidebar to open DSA Tracker, AI Tracker, Placement Tracker, and Habit Tracker.")


if "user" not in st.session_state:
    login_signup_screen()
else:
    dashboard()
