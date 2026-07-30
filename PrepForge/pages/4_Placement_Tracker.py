import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="Placement Tracker", page_icon="🎯", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
db.seed_placement_checklist(user["id"])

st.title("🎯 Placement Tracker")
st.caption("OOP / DBMS / SQL / OS / CN, soft skills, and profile readiness — the checklist recruiters look for.")

items = db.get_placement_checklist(user["id"])
df = pd.DataFrame(items)

done_count = int(df["done"].sum())
st.metric("Placement Readiness", f"{done_count}/{len(df)} ({round(done_count/len(df)*100,1)}%)")

fig = px.bar(
    df.groupby("category")["done"].mean().reset_index().assign(pct=lambda d: d["done"] * 100),
    x="category", y="pct", title="Readiness % by category", color="category",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

for cat in df["category"].unique():
    st.subheader(cat)
    cat_rows = df[df["category"] == cat]
    cols = st.columns(3)
    for i, (_, row) in enumerate(cat_rows.iterrows()):
        with cols[i % 3]:
            checked = st.checkbox(row["item"], value=bool(row["done"]), key=f"pl-{row['id']}")
            if checked != bool(row["done"]):
                db.toggle_placement_item(row["id"], checked)
                st.rerun()
