"""
app.py
------
SmartCart Customer Segment Predictor -- Streamlit app.

Loads saved model artifacts (from train.py) and provides:
  - Tab 1: a form to predict a new customer's segment
  - Tab 2: an overview of all 4 segments with charts

Run:
    streamlit run app.py
"""

import pandas as pd
import numpy as np
import joblib
import streamlit as st

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(BASE_DIR, "artifacts")

st.set_page_config(page_title="SmartCart Segment Predictor", page_icon="🛒", layout="wide")

# ---------- Styling ----------
PERSONA_COLORS = {
    0: "#F2994A",  # amber - budget window shoppers
    1: "#27AE60",  # green - premium loyal
    2: "#EB5757",  # red - budget least engaged / at risk
    3: "#2D9CDB",  # blue - premium campaign responsive
}
PERSONA_ICONS = {
    0: "🛒",
    1: "💎",
    2: "⚠️",
    3: "🚀",
}

st.markdown("""
<style>
.big-title {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #2D9CDB, #27AE60);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
}
.subtitle {
    color: #6b6b6b;
    font-size: 1.05rem;
    margin-top: 0.2rem;
}
.result-card {
    padding: 1.4rem 1.6rem;
    border-radius: 14px;
    color: white;
    margin-top: 1rem;
}
.result-card h2 { margin: 0 0 0.3rem 0; }
.result-card p { margin: 0; opacity: 0.95; }
.persona-chip {
    display: inline-block;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    color: white;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_artifacts():
    ohe = joblib.load(f"{ARTIFACTS_DIR}/ohe.pkl")
    scaler = joblib.load(f"{ARTIFACTS_DIR}/scaler.pkl")
    pca = joblib.load(f"{ARTIFACTS_DIR}/pca.pkl")
    centroids = joblib.load(f"{ARTIFACTS_DIR}/cluster_centroids.pkl")
    personas = joblib.load(f"{ARTIFACTS_DIR}/cluster_personas.pkl")
    recommendations = joblib.load(f"{ARTIFACTS_DIR}/cluster_recommendations.pkl")
    reference_date = joblib.load(f"{ARTIFACTS_DIR}/reference_date.pkl")
    try:
        profile = joblib.load(f"{ARTIFACTS_DIR}/cluster_profile.pkl")
    except FileNotFoundError:
        profile = None
    return ohe, scaler, pca, centroids, personas, recommendations, reference_date, profile


def predict_new_customer(raw_customer: dict, ohe, scaler, pca, centroids, reference_date):
    row = pd.DataFrame([raw_customer])

    row["Age"] = 2026 - row["Year_Birth"]
    row["Dt_Customer"] = pd.to_datetime(row["Dt_Customer"], dayfirst=True)
    row["Customer_Tenure_Days"] = (reference_date - row["Dt_Customer"]).dt.days
    row["Total_Spending"] = (row["MntWines"] + row["MntFruits"] + row["MntMeatProducts"]
                              + row["MntFishProducts"] + row["MntSweetProducts"] + row["MntGoldProds"])
    row["Total_Children"] = row["Kidhome"] + row["Teenhome"]
    row["Education"] = row["Education"].replace({
        "Basic": "Undergraduate", "2n Cycle": "Undergraduate",
        "Graduation": "Graduate",
        "Master": "Postgraduate", "PhD": "Postgraduate"
    })
    row["Living_With"] = row["Marital_Status"].replace({
        "Married": "Partner", "Together": "Partner",
        "Single": "Alone", "Divorced": "Alone", "Widow": "Alone", "Absurb": "Alone", "YOLO": "Alone"
    })

    row_cleaned = row.drop(columns=["Year_Birth", "Marital_Status", "Kidhome", "Teenhome",
                                     "Dt_Customer", "MntWines", "MntFruits", "MntMeatProducts",
                                     "MntFishProducts", "MntSweetProducts", "MntGoldProds"])

    enc_row = ohe.transform(row_cleaned[["Education", "Living_With"]])
    enc_row_df = pd.DataFrame(enc_row.toarray(), columns=ohe.get_feature_names_out(["Education", "Living_With"]))
    row_encoded = pd.concat([row_cleaned.drop(columns=["Education", "Living_With"]).reset_index(drop=True),
                              enc_row_df], axis=1)

    row_encoded = row_encoded.reindex(columns=scaler.feature_names_in_, fill_value=0)

    row_scaled = scaler.transform(row_encoded)
    row_pca = pca.transform(row_scaled)

    distances = np.linalg.norm(centroids.values - row_pca, axis=1)
    predicted_cluster = int(np.argmin(distances))
    return predicted_cluster


ohe, scaler, pca, centroids, personas, recommendations, reference_date, profile = load_artifacts()

st.markdown('<div class="big-title">🛒 SmartCart Segment Predictor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Unsupervised customer segmentation, powered by K-Means / Agglomerative Clustering</div>', unsafe_allow_html=True)
st.write("")

tab_predict, tab_overview = st.tabs(["🔮 Predict a customer", "📊 Segment overview"])

# ---------------- TAB 1: PREDICT ----------------
with tab_predict:
    st.write("Enter a customer's details below and the model will instantly predict which segment they belong to.")

    with st.form("customer_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Demographics**")
            year_birth = st.number_input("Year of birth", min_value=1900, max_value=2020, value=1980)
            education = st.selectbox("Education", ["Graduation", "PhD", "Master", "Basic", "2n Cycle"])
            marital_status = st.selectbox("Marital status", ["Single", "Married", "Together", "Divorced", "Widow"])
            income = st.number_input("Yearly income", min_value=0, value=60000, step=1000)
            kidhome = st.number_input("Small children at home", min_value=0, max_value=5, value=0)
            teenhome = st.number_input("Teenagers at home", min_value=0, max_value=5, value=0)
            dt_customer = st.date_input("Date joined SmartCart")
            recency = st.number_input("Days since last purchase", min_value=0, value=30)

        with col2:
            st.markdown("**💰 Spending (last 2 years)**")
            mnt_wines = st.number_input("Spent on wines", min_value=0, value=200)
            mnt_fruits = st.number_input("Spent on fruits", min_value=0, value=20)
            mnt_meat = st.number_input("Spent on meat products", min_value=0, value=150)
            mnt_fish = st.number_input("Spent on fish products", min_value=0, value=30)
            mnt_sweets = st.number_input("Spent on sweet products", min_value=0, value=20)
            mnt_gold = st.number_input("Spent on gold products", min_value=0, value=40)

        st.markdown("**🛍️ Shopping behaviour**")
        col3, col4, col5 = st.columns(3)
        with col3:
            num_deals = st.number_input("Purchases using discounts", min_value=0, value=2)
            num_web = st.number_input("Web purchases", min_value=0, value=4)
        with col4:
            num_catalog = st.number_input("Catalog purchases", min_value=0, value=3)
            num_store = st.number_input("Store purchases", min_value=0, value=5)
        with col5:
            num_web_visits = st.number_input("Website visits per month", min_value=0, value=5)
            complain = st.selectbox("Complained in last 2 years?", ["No", "Yes"])

        response = st.radio("Responded to the last marketing campaign?", ["No", "Yes"], horizontal=True)

        submitted = st.form_submit_button("🔮 Predict segment", use_container_width=True)

    if submitted:
        raw_customer = {
            "Year_Birth": year_birth, "Education": education, "Marital_Status": marital_status,
            "Income": income, "Kidhome": kidhome, "Teenhome": teenhome,
            "Dt_Customer": dt_customer.strftime("%d-%m-%Y"), "Recency": recency,
            "MntWines": mnt_wines, "MntFruits": mnt_fruits, "MntMeatProducts": mnt_meat,
            "MntFishProducts": mnt_fish, "MntSweetProducts": mnt_sweets, "MntGoldProds": mnt_gold,
            "NumDealsPurchases": num_deals, "NumWebPurchases": num_web, "NumCatalogPurchases": num_catalog,
            "NumStorePurchases": num_store, "NumWebVisitsMonth": num_web_visits,
            "Complain": 1 if complain == "Yes" else 0, "Response": 1 if response == "Yes" else 0,
        }

        cluster = predict_new_customer(raw_customer, ohe, scaler, pca, centroids, reference_date)
        persona = personas[cluster]
        recommendation = recommendations[cluster]
        color = PERSONA_COLORS.get(cluster, "#555")
        icon = PERSONA_ICONS.get(cluster, "🏷️")

        st.markdown(f"""
        <div class="result-card" style="background:{color};">
            <h2>{icon} {persona}</h2>
            <p>{recommendation}</p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total spending (2yr)", f"${raw_customer['MntWines'] + raw_customer['MntFruits'] + raw_customer['MntMeatProducts'] + raw_customer['MntFishProducts'] + raw_customer['MntSweetProducts'] + raw_customer['MntGoldProds']:,}")
        c2.metric("Yearly income", f"${income:,}")
        c3.metric("Web visits / month", num_web_visits)

# ---------------- TAB 2: OVERVIEW ----------------
with tab_overview:
    st.write("How SmartCart's customer base breaks down into 4 segments (based on the training data).")

    if profile is not None:
        cols = st.columns(4)
        for i, col in enumerate(cols):
            if i in profile.index:
                color = PERSONA_COLORS.get(i, "#555")
                icon = PERSONA_ICONS.get(i, "🏷️")
                with col:
                    st.markdown(f"""
                    <span class="persona-chip" style="background:{color};">{icon} {personas[i]}</span>
                    """, unsafe_allow_html=True)
                    st.metric("Avg. income", f"${profile.loc[i, 'Income']:,.0f}")
                    st.metric("Avg. spend", f"${profile.loc[i, 'Total_Spending']:,.0f}")
                    st.metric("Response rate", f"{profile.loc[i, 'Response']*100:.1f}%")
                    st.caption(f"{int(profile.loc[i, 'count'])} customers")

        st.write("")
        st.markdown("**Average income vs. spending by segment**")
        chart_df = profile[["Income", "Total_Spending"]].rename(
            index={i: personas[i] for i in profile.index}
        )
        st.bar_chart(chart_df)

        st.markdown("**Campaign response rate by segment**")
        resp_df = (profile[["Response"]] * 100).rename(
            index={i: personas[i] for i in profile.index}, columns={"Response": "Response rate (%)"}
        )
        st.bar_chart(resp_df)
    else:
        st.warning("Run train.py first to generate the segment overview data (cluster_profile.pkl not found).")
