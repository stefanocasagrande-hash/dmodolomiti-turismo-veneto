import os
import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from etl import load_data
from sklearn.linear_model import LinearRegression
import streamlit.components.v1 as components

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
        default=sorted(df_long["Anno"].unique())[-2:]
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
# CONFRONTO RAPIDO TRA ANNI SELEZIONATI (MESI DISPONIBILI)
# ---------------------------------------------------------
ultimo_anno = int(df_long["Anno"].max())
if ultimo_anno in anni and len(anni) >= 2 and len(paesi) > 0:
    anno_precedente = max([a for a in anni if a < ultimo_anno])

    mesi_attivi = (
        df_long[(df_long["Anno"] == ultimo_anno) & (df_long["Paese"].isin(paesi))]
        .groupby("Mese", as_index=False)["Presenze"]
        .sum()
    )
    mesi_attivi = mesi_attivi[mesi_attivi["Presenze"] > 0]["Mese"].tolist()

    if len(mesi_attivi) > 0:
        somma_ultimo = df_long[
            (df_long["Anno"] == ultimo_anno) &
            (df_long["Mese"].isin(mesi_attivi)) &
            (df_long["Paese"].isin(paesi))
        ]["Presenze"].sum()

        somma_precedente = df_long[
            (df_long["Anno"] == anno_precedente) &
            (df_long["Mese"].isin(mesi_attivi)) &
            (df_long["Paese"].isin(paesi))
        ]["Presenze"].sum()

        diff_assoluta = somma_ultimo - somma_precedente
        diff_percentuale = (diff_assoluta / somma_precedente * 100) if somma_precedente != 0 else None

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
        index=["Mese", "Paese"], columns="Anno", values="Presenze", aggfunc="sum"
    ).reset_index()

    try:
        anni_sorted = sorted(anni)
        if len(anni_sorted) == 2:
            a1, a2 = anni_sorted
            pivot["Differenza assoluta"] = pivot[a2] - pivot[a1]
            pivot["Differenza %"] = ((pivot[a2] - pivot[a1]) / pivot[a1].replace(0, pd.NA) * 100).round(2)
    except Exception as e:
        st.error(f"Errore nel calcolo delle differenze: {e}")

    for col in pivot.select_dtypes(include="number").columns:
        pivot[col] = pivot[col].fillna(0)

    def color_diff(val):
        if val > 0: return "color:green;font-weight:bold;"
        elif val < 0: return "color:red;font-weight:bold;"
        else: return "color:gray;"
    st.dataframe(
        pivot.style.applymap(color_diff, subset=["Differenza assoluta", "Differenza %"]),
        use_container_width=True,
    )

# ---------------------------------------------------------
# 🏆 CLASSIFICA DEI 10 PAESI CON PIÙ PRESENZE
# ---------------------------------------------------------
st.subheader("🏆 Classifica dei 10 Paesi con più presenze")
df_top = (
    df_long[df_long["Anno"].isin(anni)]
    .query("~Paese.str.contains('Totale', case=False, na=False)")
    .groupby(["Anno", "Paese"], as_index=False)["Presenze"].sum()
    .sort_values(["Anno", "Presenze"], ascending=[True, False])
)
df_top["Posizione"] = df_top.groupby("Anno")["Presenze"].rank(method="first", ascending=False).astype(int)
df_top = df_top.groupby("Anno").head(10)

for anno in sorted(df_top["Anno"].unique()):
    subset = df_top[df_top["Anno"] == anno]
    st.markdown(f"### 🗓️ Anno {anno}")
    html = """
    <style>.ranking-table{width:100%;border-collapse:collapse;font-family:Inter,sans-serif;font-size:15px;}
    .ranking-table th{background-color:#004c6d;color:white;padding:8px;text-align:left;}
    .ranking-table td{padding:8px;border-bottom:1px solid #ddd;}
    .ranking-table tr:nth-child(even){background-color:#f9f9f9;}
    .ranking-table tr:hover{background-color:#f1f1f1;}
    .position{font-weight:bold;color:#004c6d;text-align:center;width:50px;}</style>
    <table class="ranking-table"><thead><tr><th class="position">#</th><th>Paese</th><th style="text-align:right;">Presenze</th></tr></thead><tbody>
    """
    for _, r in subset.iterrows():
        icon = "🥇" if r["Posizione"]==1 else "🥈" if r["Posizione"]==2 else "🥉" if r["Posizione"]==3 else r["Posizione"]
        html += f"<tr><td class='position'>{icon}</td><td>{r['Paese']}</td><td style='text-align:right;'>{r['Presenze']:,}</td></tr>"
    html += "</tbody></table>"
    components.html(html, height=min(600, 60 + len(subset) * 30))

# ---------------------------------------------------------
# 🔍 ANALISI PATTERN E MERCATI PROMETTENTI (mesi comparabili)
# ---------------------------------------------------------
from sklearn.linear_model import LinearRegression
import numpy as np
import altair as alt

st.markdown("""
### 🔍 Analisi dei pattern e mercati promettenti
Analizza **l’andamento delle presenze turistiche per ciascun Paese**, considerando solo i **mesi effettivamente alimentati nell’ultimo anno disponibile**.  
I confronti tra anni sono quindi **omogenei e privi di distorsioni** dovute a mesi mancanti.
""")

# 🧾 Legenda
with st.expander("📘 Legenda indicatori di questa sezione"):
    st.markdown("""
    - **Trend medio (mesi attivi)** → crescita media annua delle presenze (in numero di presenze).  
    - **Variazione % ultimo anno** → variazione percentuale tra l’ultimo anno e quello precedente (solo mesi disponibili).  
    - **Presenze ultimo anno (mesi attivi)** → totale presenze registrate nei mesi effettivamente alimentati dell’ultimo anno.  
    - **Indice potenziale (0–100)** → combinazione normalizzata di trend e variazione percentuale recente.  
    """)

# Filtriamo fuori i totali
df_filtrato = df_long[~df_long["Paese"].str.contains("Totale stranieri", case=False, na=False)]

ultimo_anno = int(df_filtrato["Anno"].max())
mesi_attivi_ultimo = (
    df_filtrato[df_filtrato["Anno"] == ultimo_anno]
    .groupby("Mese", as_index=False)["Presenze"]
    .sum()
)
mesi_attivi_ultimo = mesi_attivi_ultimo[mesi_attivi_ultimo["Presenze"] > 0]["Mese"].tolist()

paesi_analisi = []
for paese, dfp in df_filtrato.groupby("Paese"):
    dfp_filtrato = dfp[dfp["Mese"].isin(mesi_attivi_ultimo)]
    trend_data = dfp_filtrato.groupby("Anno")["Presenze"].sum().reset_index().sort_values("Anno")

    if trend_data["Anno"].nunique() >= 3:
        X = trend_data["Anno"].values.reshape(-1, 1)
        y = trend_data["Presenze"].values
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]
        pct_growth_recent = (y[-1] - y[-2]) / y[-2] * 100 if len(y) > 1 and y[-2] != 0 else np.nan

        paesi_analisi.append({
            "Paese": paese,
            "Trend medio (mesi attivi)": slope,
            "Variazione % ultimo anno": pct_growth_recent,
            "Presenze ultimo anno (mesi attivi)": y[-1],
        })

df_pattern = pd.DataFrame(paesi_analisi)

if not df_pattern.empty:
    df_pattern["Indice potenziale"] = (
        (df_pattern["Trend medio (mesi attivi)"].rank(pct=True) * 0.5) +
        (df_pattern["Variazione % ultimo anno"].rank(pct=True) * 0.5)
    ) * 100

    df_pattern = df_pattern.sort_values("Indice potenziale", ascending=False)

    # 🔹 Rimuoviamo le voci "Altri Paesi" dalla Top10 principale
    df_reali = df_pattern[~df_pattern["Paese"].str.contains("Altri", case=False, na=False)]
    top10_reali = df_reali.head(10)
    altri = df_pattern[df_pattern["Paese"].str.contains("Altri", case=False, na=False)].head(5)

    st.markdown(f"""
#### 📊 Valutazione quantitativa dei mercati
Analisi riferita ai mesi **{mesi_attivi_ultimo[0]}–{mesi_attivi_ultimo[-1]}** dell’anno **{ultimo_anno}**.  
La classifica mostra i mercati con maggiore **trend di crescita** e **potenziale di sviluppo**.
""")

    st.dataframe(
        top10_reali.style.format({
            "Trend medio (mesi attivi)": "{:,.0f}",
            "Variazione % ultimo anno": "{:+.2f} %",
            "Indice potenziale": "{:.1f}",
        }).background_gradient(subset=["Indice potenziale"], cmap="Greens"),
        use_container_width=True,
    )

    if not altri.empty:
        st.caption("💡 I gruppi 'Altri Paesi' rappresentano mercati minori aggregati e sono mostrati separatamente:")
        st.dataframe(
            altri[["Paese", "Indice potenziale", "Variazione % ultimo anno"]]
            .style.format({"Indice potenziale": "{:.1f}", "Variazione % ultimo anno": "{:+.2f} %"}),
            use_container_width=True,
        )

else:
    st.info("Non ci sono abbastanza anni per identificare pattern statistici affidabili.")

# ---------------------------------------------------------
# 🤖 ANALISI AUTOMATICA DEI PATTERN TURISTICI
# ---------------------------------------------------------
st.markdown("### 🤖 Analisi automatica dei pattern turistici")

df_filtrato = df_filtrato.copy()
pattern_results = []

for paese, dfp in df_filtrato.groupby("Paese"):
    dfp = dfp[dfp["Mese"].isin(mesi_attivi_ultimo)]
    if dfp["Anno"].nunique() < 3:
        continue

    by_year = dfp.groupby("Anno")["Presenze"].sum().reset_index().sort_values("Anno")

    X = by_year["Anno"].values.reshape(-1, 1)
    y = by_year["Presenze"].values
    model = LinearRegression().fit(X, y)
    slope = model.coef_[0]

    cagr = ((by_year["Presenze"].iloc[-1] / by_year["Presenze"].iloc[0]) ** (1 / (len(by_year) - 1)) - 1) * 100 if len(by_year) > 1 else np.nan

    stagionalita_abs = dfp.groupby(["Anno", "Mese"])["Presenze"].sum().groupby("Anno").std().mean()
    stagionalita_rel = dfp.groupby(["Anno", "Mese"])["Presenze"].sum().groupby("Anno").apply(lambda x: (x.std() / x.mean()) * 100).mean()

    diff = by_year["Presenze"].diff()
    anni_crescita = (diff > 0).sum()
    anni_totali = len(by_year)
    ratio_crescita = anni_crescita / max(anni_totali - 1, 1)

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
        "Crescita % media annua (CAGR)": cagr,
        "Indice di stagionalità (%)": stagionalita_rel,
        "Continuità crescita": f"{ratio_crescita*100:.1f}%",
        "Pattern rilevato": categoria
    })

df_patterns = pd.DataFrame(pattern_results)

if not df_patterns.empty:
    # Escludiamo i totali
    df_patterns = df_patterns[~df_patterns["Paese"].str.contains("Totale stranieri", case=False, na=False)]

    st.markdown("#### Classificazione dei pattern turistici (mesi comparabili)")
    st.dataframe(
        df_patterns.sort_values("Trend medio", ascending=False)
        .style.format({
            "Trend medio": "{:,.0f}",
            "Crescita % media annua (CAGR)": "{:+.2f} %",
            "Indice di stagionalità (%)": "{:.1f} %",
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

    # 🔹 Mercati promettenti reali (senza "Altri Paesi")
    promising = df_patterns[
        df_patterns["Pattern rilevato"].isin(["📈 Crescita costante", "🔁 Ciclico / variabile"])
        & (~df_patterns["Paese"].str.contains("Altri", case=False, na=False))
    ].head(10)

    if not promising.empty:
        st.markdown("#### 🌍 Mercati potenzialmente promettenti")
        st.write("Mercati con **trend positivo**, **stagionalità moderata** e **continuità di crescita elevata**.")
        st.table(
            promising[["Paese", "Pattern rilevato", "Crescita % media annua (CAGR)", "Indice di stagionalità (%)", "Continuità crescita"]]
            .sort_values("Crescita % media annua (CAGR)", ascending=False)
        )

else:
    st.info("Non ci sono abbastanza dati per identificare pattern significativi.")

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
