import streamlit as st
import plotly.express as px
import pandas as pd
from etl import load_data

# ======================
# AUTENTICAZIONE BASE
# ======================
PASSWORD = "segreta123"  # <-- qui scegli tu la password da condividere con i colleghi

st.title("🔒 Dashboard Turistica Veneto")

password = st.text_input("Inserisci password", type="password")

if password != PASSWORD:
    if password:
        st.error("❌ Password sbagliata")
    st.stop()  # interrompe l'esecuzione qui finché la password non è giusta

# Carica i dati
data = load_data("dati-mensili-per-comune")

st.set_page_config(page_title="Analisi Turistica Veneto - Mensile", layout="wide")

st.title("📊 Analisi Turistica Veneto - Presenze mensili per Comune")

# ======================
# FILTRI
# ======================
anni = st.multiselect(
    "Seleziona anno",
    sorted(data["anno"].unique()),
    default=sorted(data["anno"].unique())
)

comuni = st.multiselect(
    "Seleziona Comune",
    sorted(data["Comune"].unique()),
    default=["Cortina d'Ampezzo"]
)

mesi = st.multiselect(
    "Seleziona mesi",
    sorted(data["mese"].unique()),
    default=sorted(data["mese"].unique())
)

# Applica i filtri
df_filtered = data[
    (data["anno"].isin(anni)) &
    (data["Comune"].isin(comuni)) &
    (data["mese"].isin(mesi))
]

# ======================
# TABELLA CONFRONTO ANNI
# ======================
st.subheader("📋 Tabella presenze filtrate (con confronto anni)")

if not df_filtered.empty:
    df_pivot = df_filtered.pivot_table(
        index=["Comune", "mese"],
        columns="anno",
        values="presenze",
        aggfunc="sum"
    ).reset_index()

    # Ordina i mesi da Gen a Dic
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    df_pivot["mese"] = pd.Categorical(df_pivot["mese"], categories=ordine_mesi, ordered=True)
    df_pivot = df_pivot.sort_values(["Comune", "mese"])

    # Se ci sono esattamente 2 anni selezionati -> aggiungi differenze
    if len(anni) == 2:
        anno1, anno2 = sorted(anni)
        df_pivot["Diff assoluta"] = df_pivot[anno2] - df_pivot[anno1]
        df_pivot["Diff %"] = (
            (df_pivot["Diff assoluta"] / df_pivot[anno1]) * 100
        ).round(1).astype(str) + "%"

    st.dataframe(df_pivot)
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# GRAFICO ANDAMENTO MENSILE
# ======================
st.subheader("📈 Andamento mensile")

if not df_filtered.empty:
    fig = px.line(
        df_filtered,
        x="mese",
        y="presenze",
        color="anno",        # colori diversi per anno
        markers=True,
        facet_row="Comune"   # un grafico per ogni Comune selezionato
    )
    fig.update_layout(
        xaxis=dict(
            categoryorder="array",
            categoryarray=["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                           "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        ),
        legend_title_text="Anno"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# GRAFICO CONFRONTO COMUNI (BARRE AFFIANCATE PER ANNO)
# ======================
st.subheader("🏙️ Confronto tra Comuni")

fig_bar = px.bar(
    df_filtered,
    x="mese",
    y="presenze",
    color="anno",       # colore per anno
    barmode="group",    # barre affiancate
    facet_row="Comune"  # un grafico per ogni Comune
)

fig_bar.update_layout(
    xaxis={'categoryorder': 'array',
           'categoryarray': ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                             "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]},
    legend_title_text="Anno",
    bargap=0.15
)

st.plotly_chart(fig_bar, use_container_width=True)

# ======================
# KPI
# ======================
st.subheader("📌 Indicatori")

if not df_filtered.empty:
    kpi_table = df_filtered.groupby(["anno", "Comune"])["presenze"].sum().reset_index()
    st.dataframe(kpi_table.rename(columns={"anno": "Anno", "Comune": "Comune", "presenze": "Totale presenze"}))
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")
