import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="DSA Tracker", page_icon="💻", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("💻 DSA Tracker")
st.caption("Log every lecture / topic. Marking a topic 'Hard' auto-schedules tighter revisions.")

with st.expander("➕ Add / Log a topic", expanded=True):
    with st.form("dsa_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        lecture_no = c1.text_input("Lecture No.")
        topic = c2.text_input("Topic *")
        status = c3.selectbox("Status", ["Pending", "In Progress", "Completed"])

        c4, c5 = st.columns(2)
        difficulty = c4.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        time_spent = c5.number_input("Time spent (minutes)", min_value=0, step=5)

        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save")

    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
        else:
            db.add_dsa_entry(user["id"], lecture_no, topic, status, difficulty, time_spent, notes)
            st.success(f"Saved '{topic}'." + (" Revision schedule created." if status == "Completed" else ""))
            st.rerun()

entries = db.get_dsa_entries(user["id"])

if not entries:
    st.info("No entries yet. Add your first lecture above.")
    st.stop()

df = pd.DataFrame(entries)

st.subheader("Progress overview")
k1, k2, k3 = st.columns(3)
k1.metric("Total Topics", len(df))
k2.metric("Completed", int((df["status"] == "Completed").sum()))
k3.metric("Total Time Logged", f"{int(df['time_spent_min'].sum())} min")

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    status_counts = df["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    fig1 = px.pie(status_counts, names="status", values="count", title="Status breakdown")
    st.plotly_chart(fig1, use_container_width=True)

with chart_col2:
    diff_counts = df["difficulty"].value_counts().reset_index()
    diff_counts.columns = ["difficulty", "count"]
    fig2 = px.bar(diff_counts, x="difficulty", y="count", title="Difficulty breakdown", color="difficulty")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("🔁 Revisions due")
due = db.get_due_revisions(user["id"])
if due:
    for d in due:
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{d['topic']}** — Revision {d['which']} (was due {d['date']})")
        if c2.button("Mark done", key=f"rev-{d['id']}-{d['which']}"):
            db.mark_revision_done(d["id"], d["which"])
            st.rerun()
else:
    st.write("Nothing due today.")

st.divider()
st.subheader("All entries")
st.dataframe(
    df[["lecture_no", "topic", "status", "difficulty", "date_done", "time_spent_min", "notes"]],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Update a pending entry")
pending_df = df[df["status"] != "Completed"]
if not pending_df.empty:
    options = {f"{r['topic']} (id {r['id']})": r["id"] for _, r in pending_df.iterrows()}
    choice = st.selectbox("Pick a topic to mark complete", list(options.keys()))
    diff_for_update = st.selectbox("Confirm difficulty", ["Easy", "Medium", "Hard"], key="update_diff")
    if st.button("Mark as Completed"):
        db.update_dsa_status(options[choice], "Completed", diff_for_update)
        st.success("Marked complete — revision dates scheduled.")
        st.rerun()
else:
    st.write("Everything logged is already completed. 🎉")
