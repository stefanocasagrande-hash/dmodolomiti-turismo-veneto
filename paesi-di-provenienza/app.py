# app.py (sostituisci completamente con questo)
import os
import streamlit as st
import altair as alt
import pandas as pd
from etl import load_data

st.set_page_config(page_title="Presenze Turistiche Estero", layout="wide", page_icon="🌍")
st.title("🌍 Presenze Turistiche Estero – Analisi per Paese di Provenienza")

# ---------------------------
# Calcolo percorsi dati robusto
# ---------------------------
# Base dir relativo al file app.py — è la scelta più robusta per Streamlit Cloud e locale
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cartelle candidate (proviamo più varianti per robustezza)
candidates = [
    os.path.join(BASE_DIR, "dati-paesi-di-provenienza"),
    os.path.join(BASE_DIR, "paesi-di-provenienza", "dati-paesi-di-provenienza"),
    os.path.join(BASE_DIR, "..", "paesi-di-provenienza", "dati-paesi-di-provenienza"),
    os.path.join("/", "mount", "src", os.path.basename(BASE_DIR), "dati-paesi-di-provenienza"),  # fallback comune su Cloud
]

DATA_DIR = None
for c in candidates:
    if os.path.exists(c) and os.path.isdir(c):
        DATA_DIR = os.path.abspath(c)
        break

# Se non trovato, informiamo l'utente con istruzioni precise e mostriamo i candidates provati
if DATA_DIR is None:
    st.error("❌ La cartella 'dati-paesi-di-provenienza' non è stata trovata.")
    st.markdown("**Percorsi provati:**")
    for c in candidates:
        st.write(f"- `{c}` — {'✅ esiste' if os.path.exists(c) and os.path.isdir(c) else '❌ non esiste'}")
    st.markdown(
        "**Soluzioni rapide:**\n"
        "1. Verifica che la cartella `dati-paesi-di-provenienza` sia committata nel repository e sia nel percorso corretto.\n"
        "2. Su GitHub la struttura dovrebbe essere: `paesi-di-provenienza/dati-paesi-di-provenienza/presenze-dolomiti-estero-YYYY.txt`.\n"
        "3. Se la cartella è in un punto diverso, aggiorna `DATA_DIR` in `app.py` o sposta la cartella.\n"
    )
    st.stop()

st.write(f"📁 Cartella dati usata: `{DATA_DIR}`")

# Mostra i file trovati (debug utile su Streamlit Cloud)
files = sorted([f for f in os.listdir(DATA_DIR) if f.lower().startswith("presenze-dolomiti-estero")])
if not files:
    st.error(f"❌ Nessun file `presenze-dolomiti-estero-*.txt` trovato in `{DATA_DIR}`.")
    st.write("File presenti nella cartella:")
    st.write(sorted(os.listdir(DATA_DIR)))
    st.stop()

st.write("📂 File dati trovati:")
for f in files:
    st.write(f"- {f}")

# ---------------------------
# Caricamento dati tramite etl.py
# ---------------------------
try:
    # load_data è quella definita in etl.py: load_data(data_dir=..., prefix="presenze-dolomiti-estero")
    df_long = load_data(data_dir=DATA_DIR, prefix="presenze-dolomiti-estero")
    st.success("✅ Dati caricati correttamente.")
except Exception as e:
    st.error(f"❌ Errore nel caricamento dati: {e}")
    # log minimale per debug
    st.write("Se sei su Streamlit Cloud, controlla i log 'Manage app' -> 'Logs' per dettagli.")
    raise

# Anteprima per controllo
st.subheader("🔎 Anteprima dati (prime righe)")
st.dataframe(df_long.head(10))

st.write("Colonne:", df_long.columns.tolist())
st.write("Anni disponibili:", sorted(df_long["Anno"].unique()))
st.write("Paesi unici (prime 30):", list(sorted(df_long["Paese"].unique()))[:30])
st.write("Mesi unici:", list(df_long["Mese"].cat.categories))

# ---------------------------
# FILTRI
# ---------------------------
col1, col2, col3 = st.columns(3)

with col1:
    paesi = st.multiselect(
        "🌐 Seleziona Paese/i:",
        sorted(df_long["Paese"].unique()),
        default=[p for p in sorted(df_long["Paese"].unique())][:5]  # primi 5 come default utili per test
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
        list(df_long["Mese"].cat.categories),
        default=list(df_long["Mese"].cat.categories)
    )

# ---------------------------
# Applica filtri
# ---------------------------
df_filtered = df_long[
    df_long["Paese"].isin(paesi) &
    df_long["Anno"].isin(anni) &
    df_long["Mese"].isin(mesi)
]

if df_filtered.empty:
    st.warning("⚠️ Nessun dato trovato per i filtri selezionati. Controlla i valori mostrati sopra (Paesi / Anni / Mesi).")
    st.stop()

# ---------------------------
# GRAFICO
# ---------------------------
st.subheader("📈 Andamento mensile delle presenze")

chart = (
    alt.Chart(df_filtered)
    .mark_line(point=True)
    .encode(
        x=alt.X("Mese:N", sort=list(df_long["Mese"].cat.categories)),
        y=alt.Y("Presenze:Q", title="Numero presenze"),
        color=alt.Color("Anno:N", legend=alt.Legend(title="Anno")),
        strokeDash=alt.StrokeDash("Paese:N", legend=alt.Legend(title="Paese")),
        tooltip=["Anno", "Mese", "Paese", "Presenze"]
    )
    .properties(height=450)
)

st.altair_chart(chart, use_container_width=True)

# ---------------------------
# TABELLA CONFRONTO
# ---------------------------
if len(anni) >= 2:
    st.subheader("📊 Differenze tra anni selezionati")
    pivot = df_filtered.pivot_table(
        index=["Mese", "Paese"],
        columns="Anno",
        values="Presenze",
        aggfunc="sum"
    ).reset_index()

    # se esattamente due anni, calcolo Diff assoluta e % tra i due
    try:
        anni_sorted = sorted(anni)
        if len(anni_sorted) == 2:
            a1, a2 = anni_sorted
            pivot["Differenza assoluta"] = pivot[a2] - pivot[a1]
            pivot["Differenza %"] = ((pivot["Differenza assoluta"] / pivot[a1].replace(0, pd.NA)) * 100).round(2)
        else:
            # calcoli opzionali per più anni (differenze successive)
            for i in range(1, len(anni_sorted)):
                prev, curr = anni_sorted[i-1], anni_sorted[i]
                pivot[f"Diff_{prev}_{curr}"] = pivot[curr] - pivot[prev]
    except Exception as e:
        st.error(f"Errore nel calcolo delle differenze: {e}")

    # fillna solo colonne numeriche
    pivot = pivot.copy()
    for col in pivot.select_dtypes(include="number").columns:
        pivot[col] = pivot[col].fillna(0)

    st.dataframe(pivot)

else:
    st.info("Seleziona almeno due anni per visualizzare il confronto.")

st.markdown("---")
st.caption("Dati caricati dalla cartella 'dati-paesi-di-provenienza' relativa al file app.py.")

