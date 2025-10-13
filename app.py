import streamlit as st
import pandas as pd
import plotly.express as px
from etl import load_data, load_provincia_belluno
from pattern_analysis import analisi_stagionale, seasonal_subseries_plot, clustering_comuni

# ======================
# 🔐 PROTEZIONE PASSWORD
# ======================
st.title("📊 Dashboard Turismo Veneto")

password = st.text_input("Inserisci password per accedere", type="password")
if password != "segreta123":
    if password:
        st.error("❌ Password errata")
    st.stop()
st.success("✅ Accesso consentito")

# ======================
# 📥 CARICAMENTO DATI COMUNALI
# ======================
st.sidebar.header("⚙️ Filtri principali")

data = load_data("dati-mensili-per-comune")

if data.empty:
    st.error("❌ Nessun dato caricato. Controlla la cartella 'dati-mensili-per-comune'.")
    st.stop()

# Filtri dinamici
anni = sorted(data["anno"].dropna().unique())
comuni = sorted(data["comune"].dropna().unique())
mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

anno_sel = st.sidebar.multiselect("Seleziona Anno", anni, default=anni)
comune_sel = st.sidebar.multiselect("Seleziona Comune", comuni, default=[comuni[0]])
mesi_sel = st.sidebar.multiselect("Seleziona Mese", mesi, default=mesi)

# Filtraggio dati
df_filtered = data[
    data["anno"].isin(anno_sel) &
    data["comune"].isin(comune_sel) &
    data["mese"].isin(mesi_sel)
]

# ======================
# 🔢 INDICATORI PRINCIPALI
# ======================
st.header("📈 Indicatori principali")

tot_presenze = df_filtered["presenze"].sum()
st.metric(label="Totale Presenze (filtrate)", value=f"{tot_presenze:,}".replace(",", "."))

# ======================
# 📊 GRAFICO ANDAMENTO MENSILE
# ======================
st.subheader("📊 Andamento mensile")

if not df_filtered.empty:
    fig = px.line(
        df_filtered,
        x="mese",
        y="presenze",
        color="anno",
        markers=True,
        facet_row="comune"
    )
    fig.update_layout(
        xaxis=dict(
            categoryorder="array",
            categoryarray=mesi
        ),
        legend_title_text="Anno"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# 📊 CONFRONTO TRA MESI NEI DIVERSI ANNI
# ======================
st.subheader("📆 Confronto tra mesi nei diversi anni")

if not df_filtered.empty:
    fig_bar = px.bar(
        df_filtered,
        x="anno",
        y="presenze",
        color="mese",
        barmode="group",
        facet_row="comune"
    )
    fig_bar.update_layout(
        legend_title_text="Mese",
        bargap=0.2,
        bargroupgap=0.05,
        xaxis_title="Anno",
        yaxis_title="Presenze"
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# 🔍 ANALISI DEI PATTERN TURISTICI
# ======================
st.header("🔍 Analisi dei pattern turistici")

with st.expander("ℹ️ Cosa mostra questa sezione", expanded=True):
    st.markdown("""
    Questa sezione analizza i **pattern ricorrenti** nei dati turistici per individuare andamenti comuni o stagionali nei diversi Comuni del Veneto.

    **Contenuti:**
    - 📈 **Analisi stagionale (decomposizione)**  
      Scompone le presenze nel tempo in tre componenti: *trend*, *stagionalità* e *residuo*.
    - 📊 **Distribuzione stagionale dei mesi**  
      Mostra la dispersione delle presenze per mese e anno.
    - 🧩 **Clustering Comuni per pattern stagionale**  
      Raggruppa i Comuni con andamenti simili.
    """)

comune_sel_pattern = st.selectbox("🏙️ Seleziona un Comune", sorted(data["comune"].unique()))

# --- Analisi stagionale ---
st.subheader("📈 Analisi stagionale (decomposizione)")
with st.expander("Legenda grafico"):
    st.markdown("""
    - **Linea blu** → Andamento reale delle presenze  
    - **Linea arancione** → Trend di lungo periodo  
    - **Linea verde** → Stagionalità mensile  
    - **Residuo** → Scostamenti casuali
    """)

# Dati Comune
ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
               "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
df_comune = data[data["comune"] == comune_sel_pattern].groupby(["anno", "mese"])["presenze"].sum().reset_index()
df_comune["mese_num"] = df_comune["mese"].apply(lambda x: ordine_mesi.index(x) + 1)
df_comune["data"] = pd.to_datetime(df_comune["anno"].astype(str) + "-" + df_comune["mese_num"].astype(str) + "-01")
df_comune = df_comune.sort_values("data")[["data", "presenze"]]

analisi_stagionale(data, comune_sel_pattern)

csv_comune = df_comune.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Scarica dati analisi stagionale",
    data=csv_comune,
    file_name=f"analisi_stagionale_{comune_sel_pattern}.csv",
    mime="text/csv"
)

# --- Distribuzione stagionale ---
st.subheader("📊 Distribuzione stagionale dei mesi")
with st.expander("Legenda grafico"):
    st.markdown("""
    - Ogni **box colorato** = distribuzione presenze di un mese  
    - **Punti neri** = singoli anni  
    - Box larghi = variabilità alta, box stretti = stabilità
    """)
seasonal_subseries_plot(data, comune_sel_pattern)

# --- Clustering Comuni ---
st.subheader("🧩 Clustering Comuni per pattern stagionale")
with st.expander("Legenda grafico"):
    st.markdown("""
    - Ogni **cluster** = gruppo di Comuni con stagionalità simile  
    - Le linee colorate mostrano il profilo medio mensile  
    - Picchi estivi = Comuni turistici estivi  
    - Picchi invernali = Comuni turistici invernali
    """)

n_clusters = st.slider("Numero di cluster", 2, 6, 4)
clustering_comuni(data, n_clusters=n_clusters)

# ======================
# 🏔️ ARRIVI E PRESENZE PROVINCIA DI BELLUNO
# ======================
st.header("🏔️ Arrivi e Presenze totali - Provincia di Belluno")

df_belluno = load_provincia_belluno("dati-mensili-per-comune/dati-provincia-annuali")

if not df_belluno.empty:
    anni_disponibili = sorted(df_belluno["anno"].dropna().unique())
    anno_sel = st.selectbox("Seleziona anno", anni_disponibili, index=len(anni_disponibili)-1)
    df_anno = df_belluno[df_belluno["anno"] == anno_sel]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Totale Arrivi", f"{df_anno['arrivi'].sum():,}".replace(",", "."))
    with col2:
        st.metric("Totale Presenze", f"{df_anno['presenze'].sum():,}".replace(",", "."))

    st.subheader(f"📊 Andamento mensile provincia di Belluno ({anno_sel})")

    fig_belluno = px.bar(
        df_anno,
        x="mese",
        y=["arrivi", "presenze"],
        barmode="group",
        labels={"value": "Totale", "variable": "Indicatore"},
        color_discrete_sequence=["#1f77b4", "#ff7f0e"]
    )
    fig_belluno.update_layout(
        xaxis_title="Mese",
        yaxis_title="Numero",
        legend_title_text=""
    )
    st.plotly_chart(fig_belluno, use_container_width=True)

    st.subheader("📋 Tabella dati mensili")
    st.dataframe(df_anno)

    csv_prov = df_anno.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇️ Scarica dati provincia Belluno {anno_sel} (CSV)",
        data=csv_prov,
        file_name=f"provincia_belluno_{anno_sel}.csv",
        mime="text/csv"
    )

    # Se ci sono più anni → confronto
    if len(anni_disponibili) > 1:
        st.subheader("📈 Confronto presenze provinciali tra anni")
        fig_comp = px.line(
            df_belluno,
            x="mese",
            y="presenze",
            color="anno",
            markers=True,
            category_orders={"mese": ordine_mesi}
        )
        fig_comp.update_layout(yaxis_title="Presenze", xaxis_title="Mese")
        st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.warning("⚠️ Nessun dato disponibile per la provincia di Belluno.")
