import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="Resume & Portfolio", page_icon="📄", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
db.seed_resume_checklist(user["id"])

st.title("📄 Resume & Portfolio Tracker")

st.subheader("Resume readiness")
score = db.resume_score(user["id"])
st.metric("Resume Score", f"{score}%")

checklist = db.get_resume_checklist(user["id"])
cdf = pd.DataFrame(checklist)
for cat in cdf["category"].unique():
    st.write(f"**{cat}**")
    cat_rows = cdf[cdf["category"] == cat]
    cols = st.columns(2)
    for i, (_, row) in enumerate(cat_rows.iterrows()):
        with cols[i % 2]:
            checked = st.checkbox(row["item"], value=bool(row["done"]), key=f"resume-{row['id']}")
            if checked != bool(row["done"]):
                db.toggle_resume_item(row["id"], checked)
                st.rerun()

st.divider()

st.subheader("Portfolio items")
st.caption("Projects, deployments, certificates, blogs, LinkedIn posts — anything recruiter-visible.")

with st.form("portfolio_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    item_type = c1.selectbox("Type", ["Project", "Deployment", "Certificate", "Blog", "LinkedIn Post"])
    title = c2.text_input("Title *")
    link = c3.text_input("Link")
    submitted = st.form_submit_button("Add")
if submitted:
    if not title.strip():
        st.error("Title is required.")
    else:
        db.add_portfolio_item(user["id"], item_type, title, link)
        st.success("Added.")
        st.rerun()

items = db.get_portfolio_items(user["id"])
if items:
    idf = pd.DataFrame(items)
    fig = px.bar(idf["item_type"].value_counts().reset_index(), x="index", y="item_type",
                 labels={"index": "Type", "item_type": "Count"}, title="Portfolio breakdown")
    st.plotly_chart(fig, use_container_width=True)

    for it in items:
        c1, c2 = st.columns([5, 1])
        label = f"**[{it['item_type']}]** {it['title']}"
        if it["link"]:
            label += f"  [🔗 link]({it['link']})"
        c1.markdown(label)
        if c2.button("🗑️", key=f"del-port-{it['id']}"):
            db.delete_portfolio_item(it["id"])
            st.rerun()
else:
    st.info("No portfolio items logged yet.")
