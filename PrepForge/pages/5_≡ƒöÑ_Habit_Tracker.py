import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="Habit Tracker", page_icon="🔥", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
today_habit = db.get_or_create_today_habit(user["id"])

st.title("🔥 Habit Tracker")
st.caption("Wake up, workout, meditation, reading, coding, revision, no social media, water, sleep.")

LABELS = {
    "wake_up": "Wake Up (on time)",
    "workout": "Workout",
    "meditation": "Meditation",
    "reading": "Reading",
    "coding": "Coding",
    "revision": "Revision",
    "no_social_media": "No Social Media",
    "water": "Water intake",
    "sleep": "Sleep (7+ hrs)",
}

st.subheader(f"Today — {today_habit['log_date']}")
cols = st.columns(3)
for i, col in enumerate(db.HABIT_COLUMNS):
    with cols[i % 3]:
        checked = st.checkbox(LABELS[col], value=bool(today_habit[col]), key=f"habit-{col}")
        if checked != bool(today_habit[col]):
            db.update_habit(user["id"], today_habit["log_date"], col, checked)
            st.rerun()

st.divider()

st.subheader("Streaks")
streak_cols = st.columns(3)
for i, col in enumerate(db.HABIT_COLUMNS):
    with streak_cols[i % 3]:
        st.metric(LABELS[col], f"{db.current_streak(user['id'], col)} 🔥")

st.divider()

st.subheader("Last 30 days")
history = db.get_habit_history(user["id"], days=30)
if history:
    hdf = pd.DataFrame(history)
    hdf["completed_pct"] = hdf[db.HABIT_COLUMNS].sum(axis=1) / len(db.HABIT_COLUMNS) * 100
    fig = px.bar(hdf.sort_values("log_date"), x="log_date", y="completed_pct",
                 title="Daily completion %")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No history yet — check off today's habits above to get started.")
