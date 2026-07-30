import calendar as cal
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px

from database import db

st.set_page_config(page_title="Calendar", page_icon="📅", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("📅 Calendar")
st.caption("Activity view for your prep window. Pick any date to see what was done and what's due.")

today = date.today()
c1, c2 = st.columns(2)
year = c1.number_input("Year", value=today.year, step=1)
month = c2.selectbox("Month", list(range(1, 13)), index=today.month - 1,
                      format_func=lambda m: cal.month_name[m])

counts = db.month_activity_counts(user["id"], year, month)
days_in_month = cal.monthrange(year, month)[1]
grid = pd.DataFrame({
    "day": list(range(1, days_in_month + 1)),
    "activity": [counts.get(d, 0) for d in range(1, days_in_month + 1)],
})
fig = px.bar(grid, x="day", y="activity", title=f"Activity in {cal.month_name[month]} {year}",
             labels={"activity": "Topics completed"})
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Day detail")
picked = st.date_input("Pick a date", value=today)
detail = db.calendar_day_view(user["id"], picked.isoformat())

d1, d2 = st.columns(2)
with d1:
    st.write("**✅ Completed that day**")
    if detail["completed"]:
        for c in detail["completed"]:
            st.write(f"- {c['topic']} _({c['source']})_")
    else:
        st.write("Nothing logged for this date.")

with d2:
    st.write("**🔁 Revisions due that day**")
    if detail["revisions_due"]:
        for r in detail["revisions_due"]:
            st.write(f"- {r['topic']} (Revision {r['which']})")
    else:
        st.write("No revisions scheduled for this date.")
