import streamlit as st
import pandas as pd
import plotly.express as px
from etl import load_dati_comunali, load_provincia_belluno, load_stl_data

# ======================
# ⚙️ CONFIGURAZIONE BASE
# ======================
st.set_page_config(page_title="Dashboard Turismo Veneto", layout="wide")
st.title("📊 Dashboard Turismo Veneto")

# ======================
# 🔐 ACCESSO CON PASSWORD
# ======================
password = st.text_input("Inserisci password", type="password")
if password != "dolomiti":
    if password:
        st.error("❌ Password errata. Riprova.")
    st.stop()
st.success("✅ Accesso consentito")

# ======================
# 📥 CARICAMENTO DATI
# ======================
st.sidebar.header("⚙️ Filtri principali – Dati Comunali")

data = load_dati_comunali("dati-mensili-per-comune")
provincia = load_provincia_belluno("dati-provincia-annuali")

if data.empty:
    st.error("❌ Nessun dato comunale caricato. Controlla la cartella 'dolomiti-turismo-veneto/dati-mensili-per-comune'.")
    st.stop()
else:
    st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")

# ======================
# FILTRI COMUNALI
# ======================
anni = sorted(data["anno"].unique())
comuni = sorted(data["comune"].unique())
mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

anno_sel = st.sidebar.multiselect("Seleziona Anno (Comuni)", anni, default=anni)
comune_sel = st.sidebar.multiselect("Seleziona Comune", comuni, default=[comuni[0]])
mesi_sel = st.sidebar.multiselect("Seleziona Mese", mesi, default=mesi)

df_filtered = data[
    (data["anno"].isin(anno_sel)) &
    (data["comune"].isin(comune_sel)) &
    (data["mese"].isin(mesi_sel))
]

# ======================
# 🔢 INDICATORI PRINCIPALI – COMUNI
# ======================
st.header("📈 Indicatori principali – Comuni")

if df_filtered.empty:
    st.warning("Nessun dato disponibile per i filtri selezionati.")
else:
    for comune in comune_sel:
        st.subheader(f"🏙️ {comune}")
        cols = st.columns(len(anno_sel))
        for i, anno in enumerate(anno_sel):
            tot_pres = int(df_filtered[(df_filtered["anno"] == anno) & (df_filtered["comune"] == comune)]["presenze"].sum())
            cols[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

# ======================
# 📋 TABELLA CONFRONTO TRA ANNI E MESI (COMUNI)
# ======================
st.subheader("📊 Confronto tra anni e mesi – Differenze e variazioni (Comuni)")

if not df_filtered.empty and len(anno_sel) >= 1:
    tabella = (
        df_filtered.groupby(["anno", "comune", "mese"])["presenze"]
        .sum()
        .reset_index()
        .pivot_table(index=["comune", "mese"], columns="anno", values="presenze", fill_value=0)
    )

    if len(anno_sel) == 2:
        anni_sorted = sorted(anno_sel)
        anno_prev = anni_sorted[0]
        anno_recent = anni_sorted[1]

        tabella["Differenza"] = tabella[anno_recent] - tabella[anno_prev]
        tabella["Variazione %"] = (tabella["Differenza"] / tabella[anno_prev].replace(0, pd.NA)) * 100

        fmt = {col: "{:,.0f}".format for col in tabella.columns if isinstance(col, int)}
        fmt.update({
            "Differenza": "{:,.0f}".format,
            "Variazione %": "{:.2f}%"
        })

        st.markdown(f"**Confronto tra {anno_recent} e {anno_prev}** – differenze e variazioni calcolate come {anno_recent} − {anno_prev}.")
        st.dataframe(tabella.style.format(fmt, thousands="."))

    else:
        fmt = {col: "{:,.0f}".format for col in tabella.columns if isinstance(col, int)}
        st.dataframe(tabella.style.format(fmt, thousands="."))
else:
    st.info("Seleziona almeno un anno e un comune per visualizzare la tabella comparativa.")

# ======================
# 📊 ANDAMENTO MENSILE (Comuni)
# ======================
st.subheader("📊 Andamento mensile (Comuni)")

if not df_filtered.empty:
    fig = px.line(df_filtered, x="mese", y="presenze", color="anno", markers=True, facet_row="comune")
    fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi), legend_title_text="Anno")
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 📊 CONFRONTO TRA MESI NEI DIVERSI ANNI (Comuni)
# ======================
st.subheader("📆 Confronto tra mesi nei diversi anni (Comuni)")

if not df_filtered.empty:
    fig_bar = px.bar(df_filtered, x="anno", y="presenze", color="mese", barmode="group", facet_row="comune")
    fig_bar.update_layout(legend_title_text="Mese", bargap=0.2, bargroupgap=0.05, xaxis_title="Anno", yaxis_title="Presenze")
    st.plotly_chart(fig_bar, use_container_width=True)

# ======================
# 🏔️ SEZIONE PROVINCIA DI BELLUNO
# ======================
st.sidebar.markdown("---")
mostra_provincia = st.sidebar.checkbox("📍 Mostra dati Provincia di Belluno")

if mostra_provincia:
    st.sidebar.header("⚙️ Filtri – Provincia di Belluno")

    if provincia.empty:
        st.warning("⚠️ Nessun dato provinciale caricato.")
    else:
        anni_prov = sorted(provincia["anno"].unique())
        anni_sel_prov = st.sidebar.multiselect("Seleziona Anno (Provincia)", anni_prov, default=[anni_prov[-1]])

        st.markdown("---")
        st.header("🏔️ Provincia di Belluno – Arrivi e Presenze mensili")

        prov_filtrata = provincia[provincia["anno"].isin(anni_sel_prov)]

        st.subheader("📈 Indicatori Provincia di Belluno")
        cols_metric = st.columns(len(anni_sel_prov))
        for i, anno in enumerate(anni_sel_prov):
            prov_annuale = prov_filtrata[prov_filtrata["anno"] == anno]
            tot_arrivi = int(prov_annuale["arrivi"].sum())
            tot_pres = int(prov_annuale["presenze"].sum())
            cols_metric[i].metric(f"Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            cols_metric[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        st.subheader("📊 Andamento Arrivi mensili (Provincia di Belluno)")
        fig_arr = px.line(prov_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        fig_arr.update_layout(xaxis_title="Mese", yaxis_title="Arrivi", legend_title="Anno")
        st.plotly_chart(fig_arr, use_container_width=True)

        st.subheader("📊 Andamento Presenze mensili (Provincia di Belluno)")
        fig_pres = px.line(prov_filtrata, x="mese", y="presenze", color="anno", markers=True)
        fig_pres.update_layout(xaxis_title="Mese", yaxis_title="Presenze", legend_title="Anno")
        st.plotly_chart(fig_pres, use_container_width=True)

# ======================
# 🏞️ SEZIONE STL (Dolomiti e Belluno)
# ======================
st.sidebar.markdown("---")
mostra_stl = st.sidebar.checkbox("🏞️ Mostra dati STL – Arrivi e Presenze")

if mostra_stl:
    stl_dolomiti, stl_belluno = load_stl_data("dolomiti-turismo-veneto/stl-presenze-arrivi")

    st.sidebar.header("⚙️ Filtri – Dati STL")
    stl_tipo = st.sidebar.radio("Seleziona STL", ["Dolomiti", "Belluno"])

    df_stl = stl_dolomiti if stl_tipo == "Dolomiti" else stl_belluno
    titolo = f"🏔️ STL {stl_tipo} – Arrivi e Presenze mensili"

    if df_stl.empty:
        st.warning(f"⚠️ Nessun dato disponibile per {stl_tipo}.")
    else:
        st.markdown("---")
        st.header(titolo)

        anni_stl = sorted(df_stl["anno"].unique())
        anni_sel_stl = st.sidebar.multiselect("Seleziona Anno (STL)", anni_stl, default=[anni_stl[-1]])
        df_stl_filtrata = df_stl[df_stl["anno"].isin(anni_sel_stl)]

        st.subheader("📈 Indicatori principali (STL)")
        cols_stl = st.columns(len(anni_sel_stl))
        for i, anno in enumerate(anni_sel_stl):
            df_anno = df_stl_filtrata[df_stl_filtrata["anno"] == anno]
            tot_arrivi = int(df_anno["totale_arrivi"].sum())
            tot_pres = int(df_anno["totale_presenze"].sum())
            cols_stl[i].metric(f"Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            cols_stl[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        st.subheader("📊 Andamento Arrivi mensili (STL)")
        fig_arr = px.line(df_stl_filtrata, x="mese", y="totale_arrivi", color="anno", markers=True)
        fig_arr.update_layout(xaxis_title="Mese", yaxis_title="Arrivi", legend_title="Anno")
        st.plotly_chart(fig_arr, use_container_width=True)

        st.subheader("📊 Andamento Presenze mensili (STL)")
        fig_pres = px.line(df_stl_filtrata, x="mese", y="totale_presenze", color="anno", markers=True)
        fig_pres.update_layout(xaxis_title="Mese", yaxis_title="Presenze", legend_title="Anno")
        st.plotly_chart(fig_pres, use_container_width=True)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
