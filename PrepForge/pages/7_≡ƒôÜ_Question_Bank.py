import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="Question Bank", page_icon="📚", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("📚 Question Bank")
st.caption("LeetCode / GFG / CodeStudio questions, tagged by topic, difficulty, and company.")

with st.expander("➕ Add a question", expanded=True):
    with st.form("q_form", clear_on_submit=True):
        question = st.text_input("Question title *")
        c1, c2, c3 = st.columns(3)
        platform = c1.selectbox("Platform", ["LeetCode", "GFG", "CodeStudio", "Other"])
        topic = c2.text_input("Topic (e.g. Graphs, DP)")
        difficulty = c3.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        c4, c5 = st.columns(2)
        company = c4.text_input("Company tag (optional)")
        link = c5.text_input("Link (optional)")
        submitted = st.form_submit_button("Add")
    if submitted:
        if not question.strip():
            st.error("Question title is required.")
        else:
            db.add_question(user["id"], question, platform, topic, difficulty, company, link)
            st.success("Added.")
            st.rerun()

st.divider()

f1, f2, f3, f4 = st.columns(4)
platform_f = f1.selectbox("Platform", ["All"] + db.distinct_values(user["id"], "platform"))
topic_f = f2.selectbox("Topic", ["All"] + db.distinct_values(user["id"], "topic"))
difficulty_f = f3.selectbox("Difficulty", ["All", "Easy", "Medium", "Hard"])
company_f = f4.selectbox("Company", ["All"] + db.distinct_values(user["id"], "company"))

questions = db.get_questions(user["id"], platform_f, topic_f, difficulty_f, company_f)

if not questions:
    st.info("No questions match these filters yet — add some above.")
    st.stop()

df = pd.DataFrame(questions)

k1, k2, k3 = st.columns(3)
k1.metric("Total", len(df))
k2.metric("Solved", int((df["status"] == "Solved").sum()))
k3.metric("Solve %", f"{round((df['status']=='Solved').mean()*100,1)}%")

fig = px.pie(df, names="difficulty", title="By difficulty")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Questions")
for q in questions:
    c1, c2 = st.columns([4, 1])
    label = f"**{q['question']}** — {q['platform']} · {q['topic'] or '—'} · {q['difficulty']}"
    if q["company"]:
        label += f" · 🏢 {q['company']}"
    if q["link"]:
        label += f"  [🔗 link]({q['link']})"
    c1.markdown(label)
    new_status = c2.selectbox(
        "Status", ["Not Attempted", "Attempted", "Solved"],
        index=["Not Attempted", "Attempted", "Solved"].index(q["status"]),
        key=f"qstatus-{q['id']}", label_visibility="collapsed",
    )
    if new_status != q["status"]:
        db.update_question_status(q["id"], new_status)
        st.rerun()
