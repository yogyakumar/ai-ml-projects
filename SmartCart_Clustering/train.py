"""
train.py
--------
Ye script tera pura SmartCart clustering pipeline chalata hai
(data cleaning -> feature engineering -> encoding -> scaling -> PCA -> clustering)
aur trained objects ko 'artifacts/' folder me permanent files (.pkl) ke roop me save karta hai.

Isko ek hi baar chalana hai. Uske baad app.py in saved files ko load karke
turant naye customer ka persona predict kar sakta hai -- dobara training
karne ki zaroorat nahi.

Run:
    python train.py
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import AgglomerativeClustering

CSV_PATH = "smartcart_customers.csv"   # apni CSV isi folder me rakhna, ya path change kar dena
ARTIFACTS_DIR = "artifacts"

print("Step 1/6: Loading data...")
df = pd.read_csv(CSV_PATH)

print("Step 2/6: Cleaning...")
df["Income"] = df["Income"].fillna(df["Income"].median())

print("Step 3/6: Feature engineering...")
df["Age"] = 2026 - df["Year_Birth"]
df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"], dayfirst=True)
reference_date = df["Dt_Customer"].max()
df["Customer_Tenure_Days"] = (reference_date - df["Dt_Customer"]).dt.days
df["Total_Spending"] = (df["MntWines"] + df["MntFruits"] + df["MntMeatProducts"]
                         + df["MntFishProducts"] + df["MntSweetProducts"] + df["MntGoldProds"])
df["Total_Children"] = df["Kidhome"] + df["Teenhome"]
df["Education"] = df["Education"].replace({
    "Basic": "Undergraduate", "2n Cycle": "Undergraduate",
    "Graduation": "Graduate",
    "Master": "Postgraduate", "PhD": "Postgraduate"
})
df["Living_With"] = df["Marital_Status"].replace({
    "Married": "Partner", "Together": "Partner",
    "Single": "Alone", "Divorced": "Alone", "Widow": "Alone", "Absurb": "Alone", "YOLO": "Alone"
})

cols_to_drop = ["ID", "Year_Birth", "Marital_Status", "Kidhome", "Teenhome", "Dt_Customer",
                "MntWines", "MntFruits", "MntMeatProducts", "MntFishProducts",
                "MntSweetProducts", "MntGoldProds"]
df_cleaned = df.drop(columns=cols_to_drop)

print("Step 4/6: Removing outliers...")
df_cleaned = df_cleaned[(df_cleaned["Age"] < 90)]
df_cleaned = df_cleaned[(df_cleaned["Income"] < 600_000)]

print("Step 5/6: Encoding + scaling + PCA...")
cat_cols = ["Education", "Living_With"]
ohe = OneHotEncoder()
enc_cols = ohe.fit_transform(df_cleaned[cat_cols])
enc_df = pd.DataFrame(enc_cols.toarray(), columns=ohe.get_feature_names_out(cat_cols), index=df_cleaned.index)
df_encoded = pd.concat([df_cleaned.drop(columns=cat_cols), enc_df], axis=1)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_encoded)

pca = PCA(n_components=3)
X_pca = pca.fit_transform(X_scaled)

print("Step 6/6: Clustering + persona centroids...")
agg_clf = AgglomerativeClustering(n_clusters=4, linkage="ward")
labels_agg = agg_clf.fit_predict(X_pca)

cluster_centroids = pd.DataFrame(X_pca, columns=["PCA1", "PCA2", "PCA3"])
cluster_centroids["cluster"] = labels_agg
cluster_centroids = cluster_centroids.groupby("cluster").mean()

cluster_personas = {
    0: "Budget-Conscious Window Shoppers",
    1: "Premium Loyal Customers",
    2: "Budget, Least Engaged",
    3: "Premium & Campaign Responsive"
}
cluster_recommendations = {
    0: "High web visits but low purchase & low spend -> send targeted discount coupons and deal alerts.",
    1: "High income, high spend, buys via store/catalog -> offer a premium loyalty program; low churn risk.",
    2: "Lowest spend and lowest campaign response -> highest churn risk; needs re-engagement offers.",
    3: "High income, high spend AND highest campaign response -> best ROI segment; prioritise premium campaigns."
}

# Real (interpretable) averages per cluster -- used by the app's "Segment overview" charts
profile_df = df_encoded.copy()
profile_df["cluster"] = labels_agg
cluster_profile = profile_df.groupby("cluster")[
    ["Income", "Total_Spending", "NumWebVisitsMonth", "NumStorePurchases", "Response", "Age"]
].mean()
cluster_profile["count"] = profile_df.groupby("cluster").size()

import os
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
joblib.dump(ohe, f"{ARTIFACTS_DIR}/ohe.pkl")
joblib.dump(scaler, f"{ARTIFACTS_DIR}/scaler.pkl")
joblib.dump(pca, f"{ARTIFACTS_DIR}/pca.pkl")
joblib.dump(cluster_centroids, f"{ARTIFACTS_DIR}/cluster_centroids.pkl")
joblib.dump(cluster_personas, f"{ARTIFACTS_DIR}/cluster_personas.pkl")
joblib.dump(cluster_recommendations, f"{ARTIFACTS_DIR}/cluster_recommendations.pkl")
joblib.dump(reference_date, f"{ARTIFACTS_DIR}/reference_date.pkl")
joblib.dump(cluster_profile, f"{ARTIFACTS_DIR}/cluster_profile.pkl")

print(f"\nDone! All model files saved inside '{ARTIFACTS_DIR}/' folder.")
print("Ab tu app.py chala sakta hai: streamlit run app.py")
