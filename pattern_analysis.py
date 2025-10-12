import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# =========================
# 1️⃣ Analisi stagionale (trend + stagionalità + residuo)
# =========================
def analisi_stagionale(df, comune):
    """
    Mostra la decomposizione stagionale (trend, stagionalità, residuo)
    per un Comune selezionato.
    """
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    df_comune = df[df["Comune"] == comune].groupby(["anno", "mese"])["presenze"].sum().reset_index()
    df_comune["mese_num"] = df_comune["mese"].apply(lambda x: ordine_mesi.index(x) + 1)
    df_comune["data"] = pd.to_datetime(df_comune["anno"].astype(str) + "-" + df_comune["mese_num"].astype(str) + "-01")
    df_comune = df_comune.sort_values("data").set_index("data")

    if len(df_comune) < 24:
        st.warning("Servono almeno 24 punti temporali (2 anni di dati completi) per una decomposizione significativa.")
        return

    result = seasonal_decompose(df_comune["presenze"], model="additive", period=12)

    fig = result.plot()
    fig.set_size_inches(10, 6)
    st.pyplot(fig)


# =========================
# 2️⃣ Seasonal subseries plot (pattern mensili tra anni)
# =========================
def seasonal_subseries_plot(df, comune):
    """
    Visualizza la distribuzione mensile delle presenze per tutti gli anni di un Comune.
    Permette di vedere la costanza o la variabilità dei mesi.
    """
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    df_c = df[df["Comune"] == comune]

    if df_c.empty:
        st.warning(f"Nessun dato disponibile per {comune}.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=df_c, x="mese", y="presenze", order=ordine_mesi, ax=ax, palette="viridis")
    sns.stripplot(data=df_c, x="mese", y="presenze", order=ordine_mesi, color="black", alpha=0.4, ax=ax)
    ax.set_title(f"Distribuzione stagionale delle presenze - {comune}")
    ax.set_xlabel("Mese")
    ax.set_ylabel("Presenze")
    st.pyplot(fig)


# =========================
# 3️⃣ Clustering Comuni per pattern stagionale
# =========================
def clustering_comuni(df, n_clusters=4):
    """
    Raggruppa i Comuni in base alla loro stagionalità media (profilo mensile delle presenze).
    """
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    pivot = df.pivot_table(index="Comune", columns="mese", values="presenze", aggfunc="mean").fillna(0)
    pivot = pivot[ordine_mesi]

    if len(pivot) < n_clusters:
        st.warning("Numero di cluster troppo alto rispetto al numero di Comuni disponibili.")
        return

    scaler = StandardScaler()
    X = scaler.fit_transform(pivot)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    pivot["Cluster"] = model.fit_predict(X)

    st.subheader("🧩 Comuni raggruppati per pattern stagionale")
    st.dataframe(pivot.reset_index()[["Comune", "Cluster"]])

    # Grafico dei cluster medi
    cluster_means = pivot.groupby("Cluster").mean().T
    fig, ax = plt.subplots(figsize=(10, 6))
    cluster_means.plot(ax=ax)
    ax.set_title("Pattern medi dei cluster stagionali")
    ax.set_xlabel("Mese")
    ax.set_ylabel("Presenze (standardizzate)")
    st.pyplot(fig)
