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
# GESTIONE CONFRONTO PARZIALE PER L'ULTIMO ANNO DISPONIBILE
# ---------------------------------------------------------
ultimo_anno = df_long["Anno"].max()

# Identifica i mesi realmente alimentati nell'ultimo anno
mesi_attivi_ultimo_anno = (
    df_long[df_long["Anno"] == ultimo_anno]
    .groupby("Mese")["Presenze"]
    .sum()
    .reset_index()
)
mesi_attivi_ultimo_anno = mesi_attivi_ultimo_anno[mese_attivi_ultimo_anno["Presenze"] > 0]["Mese"].tolist()

# Se l'utente ha selezionato l'ultimo anno, filtra i mesi automaticamente
if ultimo_anno in anni:
    # Se è l'unico anno selezionato o è incluso in un confronto
    mesi_confronto = [
        m for m in mesi if (m in mesi_attivi_ultimo_anno or len(anni) > 1)
    ]
    df_filtered = df_filtered[df_filtered["Mese"].isin(mesi_confronto)]

    # Mostra un messaggio informativo
    if len(mesi_attivi_ultimo_anno) < len(df_long["Mese"].cat.categories):
        st.info(
            f"ℹ️ L'anno {ultimo_anno} contiene dati solo fino a **{mesi_attivi_ultimo_anno[-1]}**. "
            f"I confronti con gli anni precedenti riguardano solo i mesi disponibili."
        )

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
# CLASSIFICA DEI 10 PAESI CON PIÙ PRESENZE
# ---------------------------------------------------------
st.subheader("🏆 Classifica dei 10 Paesi con più presenze")

# Filtra solo per anno/i selezionato/i, indipendentemente dai Paesi scelti
df_top = (
    df_long[df_long["Anno"].isin(anni)]
    .copy()
)

# Rimuovi eventuali righe Totale o simili
df_top = df_top[~df_top["Paese"].str.contains("Totale", case=False, na=False)]

# Aggrega per Paese
df_top = (
    df_top.groupby(["Anno", "Paese"], as_index=False)["Presenze"]
    .sum()
    .sort_values(["Anno", "Presenze"], ascending=[True, False])
)

# Prendi solo i top 10 per ciascun anno
df_top = df_top.groupby("Anno").head(10)

# Aggiungi colonna "Posizione"
df_top["Posizione"] = df_top.groupby("Anno")["Presenze"].rank(method="first", ascending=False).astype(int)

# Ordina per anno e posizione
df_top = df_top.sort_values(["Anno", "Posizione"])

# --- Visualizzazione in stile classifica ---
import streamlit.components.v1 as components

for anno in sorted(df_top["Anno"].unique()):
    subset = df_top[df_top["Anno"] == anno]

    st.markdown(f"### 🗓️ Anno {anno}")

    # Crea una piccola tabella HTML con stile personalizzato
    table_html = """
    <style>
    .ranking-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Inter', sans-serif;
        font-size: 15px;
    }
    .ranking-table th {
        background-color: #004c6d;
        color: white;
        padding: 8px;
        text-align: left;
    }
    .ranking-table td {
        padding: 8px;
        border-bottom: 1px solid #ddd;
    }
    .ranking-table tr:nth-child(even) {background-color: #f9f9f9;}
    .ranking-table tr:hover {background-color: #f1f1f1;}
    .position {
        font-weight: bold;
        color: #004c6d;
        text-align: center;
        width: 50px;
    }
    </style>
    <table class="ranking-table">
        <thead>
            <tr><th class="position">#</th><th>Paese</th><th style="text-align:right;">Presenze</th></tr>
        </thead>
        <tbody>
    """

    for _, row in subset.iterrows():
        table_html += f"""
        <tr>
            <td class="position">
    {"🥇" if row['Posizione']==1 else "🥈" if row['Posizione']==2 else "🥉" if row['Posizione']==3 else row['Posizione']}
</td>
            <td>{row['Paese']}</td>
            <td style="text-align:right;">{row['Presenze']:,}</td>
        </tr>
        """

    table_html += "</tbody></table>"

    components.html(table_html, height=min(600, 60 + len(subset) * 30))

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
