import os
import streamlit as st
import altair as alt
import pandas as pd
from etl import load_data

# ---------------------------------------------------------
# CONFIGURAZIONE BASE
# ---------------------------------------------------------
st.set_page_config(page_title="Presenze Turistiche Estero", layout="wide", page_icon="🌍")
st.title("🌍 Presenze Turistiche Estero - STL DOLOMITI – Analisi per Paese di Provenienza")

# ---------------------------------------------------------
# INDIVIDUA LA CARTELLA DATI
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

candidates = [
    os.path.join(BASE_DIR, "dati-paesi-di-provenienza"),
    os.path.join(BASE_DIR, "paesi-di-provenienza", "dati-paesi-di-provenienza"),
    os.path.join(BASE_DIR, "..", "paesi-di-provenienza", "dati-paesi-di-provenienza"),
    os.path.join("/", "mount", "src", os.path.basename(BASE_DIR), "dati-paesi-di-provenienza"),
]

DATA_DIR = next((c for c in candidates if os.path.exists(c) and os.path.isdir(c)), None)

if DATA_DIR is None:
    st.error("❌ La cartella 'dati-paesi-di-provenienza' non è stata trovata.")
    st.stop()

# ---------------------------------------------------------
# CARICA I DATI
# ---------------------------------------------------------
try:
    df_long = load_data(data_dir=DATA_DIR, prefix="presenze-dolomiti-estero")
except Exception as e:
    st.error(f"❌ Errore nel caricamento dati: {e}")
    st.stop()

# ---------------------------------------------------------
# FILTRI
# ---------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    paesi = st.multiselect(
        "🌐 Seleziona Paese/i:",
        sorted(df_long["Paese"].unique()),
        default=["Germania"] if "Germania" in df_long["Paese"].values else None
    )

with col2:
    anni = st.multiselect(
        "📅 Seleziona Anno/i:",
        sorted(df_long["Anno"].unique()),
        default=sorted(df_long["Anno"].unique())[-2:] if len(df_long["Anno"].unique()) >= 2 else sorted(df_long["Anno"].unique())
    )

with col3:
    mesi = st.multiselect(
        "🗓️ Seleziona Mese/i:",
        [m for m in df_long["Mese"].cat.categories if m in df_long["Mese"].unique()],
        default=[m for m in df_long["Mese"].cat.categories if m in df_long["Mese"].unique()]
    )

# ---------------------------------------------------------
# FILTRAGGIO
# ---------------------------------------------------------
df_filtered = df_long[
    df_long["Paese"].isin(paesi)
    & df_long["Anno"].isin(anni)
    & df_long["Mese"].isin(mesi)
]

if df_filtered.empty:
    st.warning("⚠️ Nessun dato trovato per i filtri selezionati.")
    st.stop()

# ---------------------------------------------------------
# GRAFICO PRINCIPALE
# ---------------------------------------------------------
st.subheader("📈 Andamento mensile delle presenze")

chart = (
    alt.Chart(df_filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("Mese:N", sort=df_long["Mese"].cat.categories),
        y=alt.Y("Presenze:Q", title="Numero presenze"),
        color=alt.Color("Anno:N", legend=alt.Legend(title="Anno")),
        strokeDash=alt.StrokeDash("Paese:N", legend=alt.Legend(title="Paese")),
        tooltip=["Anno", "Mese", "Paese", "Presenze"]
    )
    .properties(height=450)
)

st.altair_chart(chart, use_container_width=True)

# ---------------------------------------------------------
# TABELLA COMPARATIVA
# ---------------------------------------------------------
if len(anni) >= 2:
    st.subheader("📊 Differenze tra anni selezionati")

    pivot = df_filtered.pivot_table(
        index=["Mese", "Paese"],
        columns="Anno",
        values="Presenze",
        aggfunc="sum"
    ).reset_index()

    try:
        anni_sorted = sorted(anni)
        if len(anni_sorted) == 2:
            a1, a2 = anni_sorted
            pivot["Differenza assoluta"] = pivot[a2] - pivot[a1]
            pivot["Differenza %"] = ((pivot["Differenza assoluta"] / pivot[a1].replace(0, pd.NA)) * 100).round(2)
        else:
            for i in range(1, len(anni_sorted)):
                prev, curr = anni_sorted[i - 1], anni_sorted[i]
                pivot[f"Differenza {prev}-{curr}"] = pivot[curr] - pivot[prev]
                pivot[f"Differenza % {prev}-{curr}"] = ((pivot[curr] - pivot[prev]) / pivot[prev].replace(0, pd.NA) * 100).round(2)
    except Exception as e:
        st.error(f"Errore nel calcolo delle differenze: {e}")

    # Correzione fillna solo per colonne numeriche
    for col in pivot.select_dtypes(include="number").columns:
        pivot[col] = pivot[col].fillna(0)

    st.dataframe(pivot)

else:
    st.info("Seleziona almeno due anni per visualizzare le differenze.")

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
