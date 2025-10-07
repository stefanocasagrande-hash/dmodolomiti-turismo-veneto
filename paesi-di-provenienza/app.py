import os
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="Presenze Dolomiti Estero", layout="wide")

st.title("📊 Presenze Turistiche - Dolomiti (Estero)")
st.markdown("Confronto tra anni, paesi e mesi - dati ufficiali Veneto")

# --- Percorso dei dati ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "dati-paesi-di-provenienza")

# --- Carica tutti i file disponibili ---
all_data = []
for file in os.listdir(DATA_DIR):
    if file.startswith("presenze-dolomiti-estero") and file.endswith(".txt"):
        try:
            anno = int(file.split("-")[-1].split(".")[0])
            path = os.path.join(DATA_DIR, file)
            df = pd.read_csv(path, sep=";", header=1, engine="python")
            df = df.rename(columns={df.columns[0]: "Mese"})
            df["Anno"] = anno
            all_data.append(df)
        except Exception as e:
            st.warning(f"Errore nel caricamento di {file}: {e}")

# --- Unisci tutti i dati ---
if not all_data:
    st.error("❌ Nessun file trovato nella cartella 'dati-paesi-di-provenienza'")
    st.stop()

df = pd.concat(all_data, ignore_index=True)

# --- Trasforma i dati in formato lungo ---
df_long = df.melt(id_vars=["Mese", "Anno"], var_name="Paese", value_name="Presenze")
df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce")
df_long = df_long.dropna(subset=["Presenze"])

# --- Pulisci i mesi (rimuove numeri iniziali tipo '01Gennaio') ---
df_long["Mese"] = df_long["Mese"].astype(str).str.replace(r"^\d+", "", regex=True)

# --- Ordine mesi ---
mesi_ordine = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
]
df_long["Mese"] = pd.Categorical(df_long["Mese"], categories=mesi_ordine, ordered=True)

# --- FILTRI ---
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

with col3:
    mesi = st.multiselect(
        "🗓️ Seleziona Mese/i:",
        options=mesi_ordine,
        default=mesi_ordine
    )

# --- FILTRA DATI ---
df_filtered = df_long[
    (df_long["Paese"].isin(paesi)) &
    (df_long["Anno"].isin(anni)) &
    (df_long["Mese"].isin(mesi))
]

if df_filtered.empty:
    st.warning("⚠️ Nessun dato trovato per i filtri selezionati.")
    st.stop()

# --- GRAFICO ---
chart = (
    alt.Chart(df_filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("Mese", sort=mesi_ordine, title="Mese"),
        y=alt.Y("Presenze:Q", title="Numero di presenze"),
        color=alt.Color("Anno:N", title="Anno", scale=alt.Scale(scheme="tableau10")),
        strokeDash=alt.StrokeDash("Paese:N", title="Paese"),
        tooltip=["Anno", "Paese", "Mese", "Presenze"]
    )
    .properties(width=1000, height=500, title="Andamento delle presenze per Paese e Anno")
    .interactive()
)

st.altair_chart(chart, use_container_width=True)

# --- TABELLA CON DIFFERENZE ---
if len(anni) >= 2:
    pivot = df_filtered.pivot_table(
        index=["Mese", "Paese"], columns="Anno", values="Presenze", aggfunc="sum"
    ).reset_index()

    # Calcolo differenze tra due anni selezionati
    if len(anni) == 2:
        anno1, anno2 = sorted(anni)
        pivot["Diff Assoluta"] = pivot[anno2] - pivot[anno1]
        pivot["Diff %"] = ((pivot["Diff Assoluta"] / pivot[anno1]) * 100).round(2)
        st.markdown("### 📈 Differenze tra anni selezionati")
        st.dataframe(pivot.fillna(0))
    else:
        st.info("Seleziona esattamente due anni per visualizzare le differenze.")
else:
    st.info("Seleziona almeno due anni per visualizzare il confronto.")

st.markdown("---")
st.caption("Dati caricati automaticamente dai file .txt nella cartella 'dati-paesi-di-provenienza'.")
