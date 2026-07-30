import streamlit as st

from database import db

st.set_page_config(page_title="AI Mentor", page_icon="🧠", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("🧠 AI Mentor")
st.caption("Tell it what you did today — it suggests tomorrow's plan, questions, revision, and weak spots.")

api_key = st.secrets.get("GEMINI_API_KEY", None)

if not api_key:
    st.error(
        "No Gemini API key found. Copy `.streamlit/secrets.toml.example` to "
        "`.streamlit/secrets.toml` and paste your key there (get one free at "
        "aistudio.google.com → API Keys). This file is git-ignored, so it's safe."
    )
    st.stop()

import google.generativeai as genai

genai.configure(api_key=api_key)
MODEL_NAME = st.sidebar.text_input(
    "Model", value="gemini-2.0-flash",
    help="If this model errors, check available model names at aistudio.google.com and swap it here.",
)


def build_context():
    dsa = db.get_dsa_entries(user["id"])
    pending = [d["topic"] for d in dsa if d["status"] != "Completed"][:10]
    due = db.get_due_revisions(user["id"])
    weak = db.get_weak_topics(user["id"])
    return {
        "pending_topics": pending,
        "revisions_due": [f"{d['topic']} (rev {d['which']})" for d in due],
        "weak_topics": [w["topic"] for w in weak],
    }


SYSTEM_PROMPT = """You are an AI study mentor for a B.Tech CSE student preparing for placements
and an AI/ML career. Be direct, encouraging, and specific — no generic motivational fluff.
When the student reports what they completed, respond with:
1. A short acknowledgment
2. What to study tomorrow (pick from their pending topics if relevant)
3. 2-3 practice questions on today's topic
4. Revision reminders if any are due
5. Weak topics to keep an eye on
Keep it concise — bullet points, not paragraphs."""

if "mentor_history" not in st.session_state:
    st.session_state["mentor_history"] = []

for msg in st.session_state["mentor_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("e.g. I completed Lecture 25 on Graphs today")

if prompt:
    st.session_state["mentor_history"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    ctx = build_context()
    full_prompt = f"""{SYSTEM_PROMPT}

Student's current data:
- Pending topics: {ctx['pending_topics']}
- Revisions due: {ctx['revisions_due']}
- Weak (Hard-marked) topics: {ctx['weak_topics']}

Student just said: "{prompt}"
"""

    with st.chat_message("assistant"):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(full_prompt)
            reply = response.text
        except Exception as e:
            reply = (
                f"⚠️ Couldn't reach Gemini: {e}\n\n"
                "Check: (1) the model name in the sidebar, (2) that your API key is valid, "
                "(3) you have internet access."
            )
        st.markdown(reply)

    st.session_state["mentor_history"].append({"role": "assistant", "content": reply})
