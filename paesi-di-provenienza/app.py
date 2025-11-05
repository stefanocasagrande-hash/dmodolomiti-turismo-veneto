import os
import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
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
# SINTESI CONFRONTO TRA ULTIMO ANNO E ANNO PRECEDENTE (PER PAESE/I SELEZIONATI)
# ---------------------------------------------------------
ultimo_anno = int(df_long["Anno"].max())

# Mostra la sezione solo se:
# - l'utente ha selezionato l'ultimo anno
# - è stato selezionato almeno un altro anno
# - e almeno un Paese
if ultimo_anno in anni and len(anni) >= 2 and len(paesi) > 0:
    anno_precedente = max([a for a in anni if a < ultimo_anno])

    # Trova i mesi con dati > 0 nell'ultimo anno (per i Paesi selezionati)
    mesi_attivi = (
        df_long[(df_long["Anno"] == ultimo_anno) & (df_long["Paese"].isin(paesi))]
        .groupby("Mese", as_index=False)["Presenze"]
        .sum()
    )
    mesi_attivi = mesi_attivi[mesi_attivi["Presenze"] > 0]["Mese"].tolist()

    if len(mesi_attivi) > 0:
        # Somma le presenze solo per i mesi disponibili dell'ultimo anno e dell'anno precedente
        somma_ultimo = (
            df_long[
                (df_long["Anno"] == ultimo_anno)
                & (df_long["Mese"].isin(mesi_attivi))
                & (df_long["Paese"].isin(paesi))
            ]["Presenze"].sum()
        )
        somma_precedente = (
            df_long[
                (df_long["Anno"] == anno_precedente)
                & (df_long["Mese"].isin(mesi_attivi))
                & (df_long["Paese"].isin(paesi))
            ]["Presenze"].sum()
        )

        diff_assoluta = somma_ultimo - somma_precedente
        diff_percentuale = (
            (diff_assoluta / somma_precedente * 100)
            if somma_precedente != 0
            else None
        )

        # --- Sezione di sintesi ---
        st.markdown("### 📊 Confronto rapido tra anni selezionati (mesi disponibili)")
        st.markdown(
            f"""
            <div style="background-color:#f4f9ff;padding:15px;border-radius:10px;border-left:5px solid #004c6d;">
                <b>Paese/i:</b> {', '.join(paesi)}<br>
                <b>Periodo considerato:</b> Gennaio–{mesi_attivi[-1]}<br>
                <b>Confronto:</b> {anno_precedente} → {ultimo_anno}<br><br>
                <b>Presenze {anno_precedente}:</b> {somma_precedente:,.0f}<br>
                <b>Presenze {ultimo_anno}:</b> {somma_ultimo:,.0f}<br>
                <b>Variazione assoluta:</b> {diff_assoluta:+,}<br>
                <b>Variazione percentuale:</b> {diff_percentuale:+.2f}% 
            </div>
            """,
            unsafe_allow_html=True,
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
# 🥇 TOP 5 PAESI CON MAGGIOR CRESCITA PERCENTUALE (DINAMICO)
# ---------------------------------------------------------
import numpy as np  # assicurati che sia importato in alto

# Esegui solo se sono stati selezionati almeno 2 anni
if len(anni) >= 2:
    # Identifica sempre il più recente tra quelli selezionati
    anno_corrente = max(anni)
    anno_precedente = max([a for a in anni if a < anno_corrente])

    # Trova mesi alimentati (dati > 0) per l'anno corrente
    mesi_attivi = (
        df_long[df_long["Anno"] == anno_corrente]
        .groupby("Mese", as_index=False)["Presenze"]
        .sum()
    )
    mesi_attivi = mesi_attivi[mesi_attivi["Presenze"] > 0]["Mese"].tolist()

    if len(mesi_attivi) > 0:
        # Somma presenze per Paese e anno (solo mesi attivi)
        df_confronto = (
            df_long[
                df_long["Mese"].isin(mesi_attivi)
                & df_long["Anno"].isin([anno_precedente, anno_corrente])
            ]
            .groupby(["Paese", "Anno"], as_index=False)["Presenze"]
            .sum()
        )

        # Pivot per confrontare anni
        pivot_growth = df_confronto.pivot(
            index="Paese", columns="Anno", values="Presenze"
        ).fillna(0)

        # Se mancano colonne, aggiungile
        for a in (anno_precedente, anno_corrente):
            if a not in pivot_growth.columns:
                pivot_growth[a] = 0

        # Calcolo differenze
        pivot_growth["Diff_assoluta"] = (
            pivot_growth[anno_corrente] - pivot_growth[anno_precedente]
        )

        # Calcolo % con gestione "Nuovo mercato"
        pivot_growth["Diff_percentuale"] = np.where(
            pivot_growth[anno_precedente] == 0,
            np.nan,  # gestito dopo con testo
            (pivot_growth["Diff_assoluta"] / pivot_growth[anno_precedente]) * 100,
        )

        # Crea una colonna testuale per le % formattate
        def format_percent(row):
            if row[anno_precedente] == 0 and row[anno_corrente] > 0:
                return "🆕 Nuovo mercato"
            elif pd.isna(row["Diff_percentuale"]):
                return "—"
            else:
                return f"{row['Diff_percentuale']:+.2f} %"

        pivot_growth["Δ %"] = pivot_growth.apply(format_percent, axis=1)

        # Ordina per % decrescente (gestendo nuovi mercati come +∞)
        pivot_growth["_sort_key"] = np.where(
            pivot_growth["Diff_percentuale"].isna(), 9999, pivot_growth["Diff_percentuale"]
        )
        top5_crescita = (
            pivot_growth.sort_values("_sort_key", ascending=False)
            .head(5)
            .copy()
        )

        # Stile per evidenziare Δ %
        def color_growth(val):
            if isinstance(val, str) and "🆕" in val:
                return "color:#1abc9c; font-weight:bold;"
            if isinstance(val, str) and "%" in val:
                if val.startswith("+"):
                    return "color:#2ecc71; font-weight:bold;"
                elif val.startswith("-"):
                    return "color:#e74c3c; font-weight:bold;"
            return "color:#7f8c8d; font-weight:bold;"

        st.markdown("### 🚀 Top 5 Paesi con maggiore crescita percentuale")
        st.markdown(
            f"<div style='color:#777;font-size:0.9em;'>Periodo considerato: Gennaio–{mesi_attivi[-1]} ({anno_precedente} → {anno_corrente})</div>",
            unsafe_allow_html=True,
        )

        styled = (
            top5_crescita[["Δ %", "Diff_assoluta"]]
            .rename(columns={"Diff_assoluta": "Δ assoluta"})
            .style.format({"Δ assoluta": "{:+,.0f}"})
            .applymap(color_growth, subset=["Δ %"])
        )

        st.dataframe(styled, use_container_width=True)

# ---------------------------------------------------------
# 🔍 ANALISI PATTERN E MERCATI PROMETTENTI (mesi comparabili)
# ---------------------------------------------------------
from sklearn.linear_model import LinearRegression
import numpy as np

st.markdown("### 🔍 Analisi dei pattern e mercati promettenti")

# Individua l'anno più recente e i mesi alimentati
ultimo_anno = int(df_long["Anno"].max())
mesi_attivi_ultimo = (
    df_long[df_long["Anno"] == ultimo_anno]
    .groupby("Mese", as_index=False)["Presenze"]
    .sum()
)
mesi_attivi_ultimo = mesi_attivi_ultimo[mesi_attivi_ultimo["Presenze"] > 0]["Mese"].tolist()

paesi_analisi = []
for paese, dfp in df_long.groupby("Paese"):
    # Considera solo i mesi effettivamente alimentati nell'ultimo anno
    dfp_filtrato = dfp[dfp["Mese"].isin(mesi_attivi_ultimo)]

    # Calcola le presenze totali per ogni anno (stesso intervallo di mesi)
    trend_data = (
        dfp_filtrato.groupby("Anno")["Presenze"].sum().reset_index().sort_values("Anno")
    )

    if trend_data["Anno"].nunique() >= 3:
        X = trend_data["Anno"].values.reshape(-1, 1)
        y = trend_data["Presenze"].values
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]  # crescita media annua (mesi comparabili)

        # variazione % ultimo anno vs precedente (solo mesi disponibili)
        if len(y) > 1 and y[-2] != 0:
            pct_growth_recent = (y[-1] - y[-2]) / y[-2] * 100
        else:
            pct_growth_recent = np.nan

        paesi_analisi.append(
            {
                "Paese": paese,
                "Trend medio (mesi attivi)": slope,
                "Variazione % ultimo anno": pct_growth_recent,
                "Presenze ultimo anno (mesi attivi)": y[-1],
            }
        )

df_pattern = pd.DataFrame(paesi_analisi)

# Calcolo indice di potenziale combinato (normalizzato)
if not df_pattern.empty:
    df_pattern["Indice potenziale"] = (
        (df_pattern["Trend medio (mesi attivi)"].rank(pct=True) * 0.5)
        + (df_pattern["Variazione % ultimo anno"].rank(pct=True) * 0.5)
    ) * 100

    df_pattern = df_pattern.sort_values("Indice potenziale", ascending=False)

    st.markdown(
        f"I calcoli considerano solo i mesi disponibili nell'ultimo anno ({mesi_attivi_ultimo[0]}–{mesi_attivi_ultimo[-1]})."
    )
    st.markdown(
        "Ecco i 10 Paesi che mostrano i pattern di crescita e potenziale più interessanti:"
    )
    st.dataframe(
        df_pattern.head(10)
        .style.format(
            {
                "Trend medio (mesi attivi)": "{:,.0f}",
                "Variazione % ultimo anno": "{:+.2f} %",
                "Indice potenziale": "{:.1f}",
            }
        )
        .background_gradient(subset=["Indice potenziale"], cmap="Greens"),
        use_container_width=True,
    )
else:
    st.info("Non ci sono abbastanza anni per identificare pattern statistici affidabili.")

# ---------------------------------------------------------
# 🤖 ANALISI AUTOMATICA DEI PATTERN COMUNI
# ---------------------------------------------------------
st.markdown("### 🤖 Analisi automatica dei pattern turistici")

pattern_results = []

for paese, dfp in df_long.groupby("Paese"):
    # Considera solo i mesi attivi dell'ultimo anno
    dfp = dfp[dfp["Mese"].isin(mesi_attivi_ultimo)]
    if dfp["Anno"].nunique() < 3:
        continue  # servono almeno 3 anni per analisi stabile

    # Calcola la somma per ogni anno
    by_year = dfp.groupby("Anno")["Presenze"].sum().reset_index().sort_values("Anno")

    # Trend lineare
    X = by_year["Anno"].values.reshape(-1, 1)
    y = by_year["Presenze"].values
    model = LinearRegression().fit(X, y)
    slope = model.coef_[0]

    # Calcola varianza intra-annuale (stagionalità media)
    stagionalita = (
        dfp.groupby(["Anno", "Mese"])["Presenze"].sum().groupby("Anno").std().mean()
    )

    # Verifica continuità di crescita
    diff = by_year["Presenze"].diff()
    anni_crescita = (diff > 0).sum()
    anni_totali = len(by_year)
    ratio_crescita = anni_crescita / max(anni_totali - 1, 1)

    # Classificazione del pattern
    if slope > 0 and ratio_crescita > 0.7:
        categoria = "📈 Crescita costante"
    elif slope > 0 and ratio_crescita <= 0.7:
        categoria = "🔁 Ciclico / variabile"
    elif slope < 0:
        categoria = "📉 In calo o stagnante"
    else:
        categoria = "🆕 Nuovo mercato"

    pattern_results.append({
        "Paese": paese,
        "Trend medio": slope,
        "Stagionalità media": stagionalita,
        "Anni di crescita": anni_crescita,
        "Anni totali": anni_totali,
        "Continuità crescita": f"{ratio_crescita*100:.1f}%",
        "Pattern rilevato": categoria
    })

df_patterns = pd.DataFrame(pattern_results)

if not df_patterns.empty:
    st.markdown("#### Classificazione dei pattern turistici")
    st.dataframe(
        df_patterns
        .sort_values("Trend medio", ascending=False)
        .style.format({
            "Trend medio": "{:,.0f}",
            "Stagionalità media": "{:,.0f}"
        })
        .applymap(
            lambda v: "color:#2ecc71;" if isinstance(v, str) and "Crescita" in v
            else ("color:#e67e22;" if isinstance(v, str) and "Ciclico" in v
            else ("color:#e74c3c;" if isinstance(v, str) and "calo" in v.lower()
            else ("color:#1abc9c;" if isinstance(v, str) and "Nuovo" in v else ""))),
            subset=["Pattern rilevato"]
        ),
        use_container_width=True,
    )

    # Sintesi mercati promettenti
    promising = df_patterns[df_patterns["Pattern rilevato"].isin(["📈 Crescita costante", "🔁 Ciclico / variabile"])].head(10)
    if not promising.empty:
        st.markdown("#### 🌍 Mercati potenzialmente promettenti")
        st.write("Basati su trend positivo e continuità di crescita (mesi omogenei).")
        st.table(promising[["Paese", "Pattern rilevato", "Continuità crescita"]])
else:
    st.info("Non ci sono abbastanza dati per identificare pattern significativi.")

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
