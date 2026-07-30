import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="AI Tracker", page_icon="🤖", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
db.seed_ai_topics(user["id"])

st.title("🤖 AI Tracker")
st.caption("Deep Learning → GenAI → Agentic AI → MLOps → Inference Optimization (the '30 LPA' skill map).")

topics = db.get_ai_progress(user["id"])
df = pd.DataFrame(topics)

done_count = int(df["done"].sum())
st.metric("Overall AI Track Progress", f"{done_count}/{len(df)} ({round(done_count/len(df)*100,1)}%)")

fig = px.bar(
    df.groupby("module")["done"].mean().reset_index().assign(pct=lambda d: d["done"] * 100),
    x="module", y="pct", title="Completion % by module", color="module",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

for module in df["module"].unique():
    st.subheader(module)
    module_rows = df[df["module"] == module]
    cols = st.columns(3)
    for i, (_, row) in enumerate(module_rows.iterrows()):
        with cols[i % 3]:
            checked = st.checkbox(row["topic"], value=bool(row["done"]), key=f"ai-{row['id']}")
            if checked != bool(row["done"]):
                db.toggle_ai_topic(row["id"], checked)
                st.rerun()
