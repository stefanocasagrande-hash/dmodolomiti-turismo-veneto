import streamlit as st
import altair as alt
import pandas as pd
import os
from etl import load_data

# Impostazioni Streamlit
st.set_page_config(page_title="Presenze Turistiche Estero", layout="wide")

st.title("📊 Presenze Turistiche - Dolomiti (Estero)")
st.markdown("Analisi e confronto delle presenze turistiche per Paese di provenienza e anno.")

# Percorso dinamico della cartella dati
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dati-paesi-di-provenienza")

# --- Caricamento dati ---
try:
    df_long = load_data(data_dir=DATA_DIR, prefix="presenze-dolomiti-estero")
except FileNotFoundError as e:
    st.error(f"❌ Errore nel caricamento dati: {e}")
    st.stop()

# --- Filtri ---
col1, col2, col3 = st.columns(3)

with col1:
    paesi = st.multiselect(
        "🌍 Seleziona Paese/i:",
        options=sorted(df_long["Paese"].unique()),
        default=["Germania"] if "Germania" in df_long["Paese"].unique() else []
    )

with col2:
    anni = st.multiselect(
        "📅 Seleziona Anno/i:",
        options=sorted(df_long["Anno"].unique()),
        default=sorted(df_long["Anno"].unique())
    )

mesi_ordine = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
]

with col3:
    mesi = st.multiselect(
        "🗓️ Seleziona Mese/i:",
        options=mesi_ordine,
        default=mesi_ordine
    )

# --- Applica filtri ---
df_filtered = df_long[
    (df_long["Paese"].isin(paesi)) &
    (df_long["Anno"].isin(anni)) &
    (df_long["Mese"].isin(mesi))
]

if df_filtered.empty:
    st.warning("⚠️ Nessun dato trovato per i filtri selezionati.")
    st.stop()

# --- Grafico ---
chart = (
    alt.Chart(df_filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("Mese:N", sort=mesi_ordine, title="Mese"),
        y=alt.Y("Presenze:Q", title="Numero di presenze"),
        color=alt.Color("Anno:N", title="Anno", scale=alt.Scale(scheme="tableau10")),
        strokeDash=alt.StrokeDash("Paese:N", title="Paese"),
        tooltip=["Anno", "Paese", "Mese", "Presenze"]
    )
    .properties(
        width=1000,
        height=500,
        title="Andamento delle presenze per Paese e Anno"
    )
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

# --- Tabella differenze ---
if len(anni) >= 2:
    pivot = df_filtered.pivot_table(
        index=["Mese", "Paese"], columns="Anno", values="Presenze", aggfunc="sum"
    ).reset_index()

    if len(anni) == 2:
        anno1, anno2 = sorted(anni)
        pivot["Diff Assoluta"] = pivot[anno2] - pivot[anno1]
        pivot["Diff %"] = ((pivot["Diff Assoluta"] / pivot[anno1]) * 100).round(2)

        st.markdown("### 📈 Differenze tra anni selezionati")
        st.dataframe(pivot.fillna(0))
    else:
        st.info("Seleziona esattamente due anni per visualizzare le differenze.")
else:
    st.info("Seleziona almeno due anni per confrontare i dati.")

# --- Footer ---
st.markdown("---")
st.caption("Dati caricati automaticamente dalla cartella `dati-paesi-di-provenienza`. \
Grafico generato con Altair, dashboard realizzata con Streamlit.")
