import io
from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database import db

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

if "user" not in st.session_state:
    st.warning("Please log in from the main Dashboard page first.")
    st.stop()

user = st.session_state["user"]
st.title("📈 Analytics & Weekly Report")

report = db.weekly_report(user["id"])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Topics completed (7d)", report["topics_completed"])
k2.metric("Hours studied (7d)", report["hours_studied"])
k3.metric("Pending DSA topics", report["pending_topics"])
k4.metric("Habit consistency (7d)", f"{report['habit_consistency_pct']}%")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Completion overview")
    dsa = db.get_dsa_entries(user["id"])
    ai = db.get_ai_progress(user["id"])
    placement = db.get_placement_checklist(user["id"])
    resume = db.get_resume_checklist(user["id"])

    radar_categories = ["DSA", "AI Track", "Placement", "Resume"]
    radar_values = [
        round(sum(1 for d in dsa if d["status"] == "Completed") / len(dsa) * 100, 1) if dsa else 0,
        round(sum(1 for a in ai if a["done"]) / len(ai) * 100, 1) if ai else 0,
        round(sum(1 for p in placement if p["done"]) / len(placement) * 100, 1) if placement else 0,
        db.resume_score(user["id"]),
    ]
    fig_radar = go.Figure(data=go.Scatterpolar(r=radar_values, theta=radar_categories, fill='toself'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                             title="Readiness radar")
    st.plotly_chart(fig_radar, use_container_width=True)

with right:
    st.subheader("This week's completed topics")
    week_items = [{"topic": d["topic"], "type": "DSA"} for d in report["dsa_completed"]] + \
                 [{"topic": a["topic"], "type": "AI"} for a in report["ai_completed"]]
    if week_items:
        wdf = pd.DataFrame(week_items)
        fig2 = px.pie(wdf, names="type", title="This week: DSA vs AI")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nothing completed in the last 7 days yet.")

st.divider()
st.subheader("Export weekly report")

def build_excel_report():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([{
            "Topics Completed (7d)": report["topics_completed"],
            "Hours Studied (7d)": report["hours_studied"],
            "Pending DSA Topics": report["pending_topics"],
            "Habit Consistency %": report["habit_consistency_pct"],
        }]).to_excel(writer, sheet_name="Summary", index=False)
        if report["dsa_completed"]:
            pd.DataFrame(report["dsa_completed"]).to_excel(writer, sheet_name="DSA Completed", index=False)
        if report["ai_completed"]:
            pd.DataFrame(report["ai_completed"]).to_excel(writer, sheet_name="AI Completed", index=False)
    buf.seek(0)
    return buf


def build_pdf_report():
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PrepForge — Weekly Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"User: {user['username']}   Generated: {date.today().isoformat()}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Topics completed (7d): {report['topics_completed']}", ln=True)
    pdf.cell(0, 7, f"Hours studied (7d): {report['hours_studied']}", ln=True)
    pdf.cell(0, 7, f"Pending DSA topics: {report['pending_topics']}", ln=True)
    pdf.cell(0, 7, f"Habit consistency: {report['habit_consistency_pct']}%", ln=True)
    pdf.ln(4)

    if report["dsa_completed"]:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "DSA topics completed this week", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for d in report["dsa_completed"]:
            pdf.cell(0, 6, f"- {d['topic']} ({d['difficulty']}, {d['time_spent_min']} min)", ln=True)

    return bytes(pdf.output(dest="S"))


col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "⬇️ Download Excel report",
        data=build_excel_report(),
        file_name=f"mission_os_report_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with col2:
    st.download_button(
        "⬇️ Download PDF report",
        data=build_pdf_report(),
        file_name=f"mission_os_report_{date.today().isoformat()}.pdf",
        mime="application/pdf",
    )
