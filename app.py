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
# 🔐 ACCESSO
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
stl_dolomiti, stl_belluno = load_stl_data("stl-presenze-arrivi")

if data.empty:
    st.error("❌ Nessun dato comunale caricato.")
    st.stop()
else:
    st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")

# ======================
# FILTRI COMUNALI
# ======================
anni = sorted(data["anno"].unique())
comuni = sorted(data["comune"].unique())
mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

anno_sel = st.sidebar.multiselect("Anno (Comuni)", anni, default=anni)
comune_sel = st.sidebar.multiselect("Comune", comuni, default=[comuni[0]])
mesi_sel = st.sidebar.multiselect("Mese", mesi, default=mesi)

df_filtered = data[(data["anno"].isin(anno_sel)) & (data["comune"].isin(comune_sel)) & (data["mese"].isin(mesi_sel))]

# ======================
# 📈 INDICATORI COMUNALI
# ======================
st.header("*** DASHBOARD IN LAVORAZIONE ***")
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
# 📈 ANDAMENTO MENSILE (COMUNI)
# ======================
if not df_filtered.empty:
    st.subheader("📈 Andamento mensile (Comuni)")
    fig = px.line(df_filtered, x="mese", y="presenze", color="anno", markers=True, facet_row="comune")
    fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 🏔️ PROVINCIA DI BELLUNO
# ======================
st.sidebar.markdown("---")
if st.sidebar.checkbox("📍 Mostra dati Provincia di Belluno"):
    if not provincia.empty:
        st.header("🏔️ Provincia di Belluno – Arrivi e Presenze mensili")
        anni_prov = sorted(provincia["anno"].unique())
        anni_sel_prov = st.sidebar.multiselect("Anno (Provincia)", anni_prov, default=[anni_prov[-1]])
        prov_filtrata = provincia[provincia["anno"].isin(anni_sel_prov)]

        cols = st.columns(len(anni_sel_prov))
        for i, anno in enumerate(anni_sel_prov):
            tot_arr = int(prov_filtrata[prov_filtrata["anno"] == anno]["arrivi"].sum())
            tot_pre = int(prov_filtrata[prov_filtrata["anno"] == anno]["presenze"].sum())
            cols[i].metric(f"Arrivi {anno}", f"{tot_arr:,}".replace(",", "."))
            cols[i].metric(f"Presenze {anno}", f"{tot_pre:,}".replace(",", "."))

        st.subheader("📈 Andamento Arrivi Mensili")
        st.plotly_chart(px.line(prov_filtrata, x="mese", y="arrivi", color="anno", markers=True), use_container_width=True)
        st.subheader("📈 Andamento Presenze Mensili")
        st.plotly_chart(px.line(prov_filtrata, x="mese", y="presenze", color="anno", markers=True), use_container_width=True)

# ======================
# 🏞️ STL
# ======================
st.sidebar.markdown("---")
if st.sidebar.checkbox("📍 Mostra dati STL"):
    st.sidebar.header("⚙️ Filtri – STL")
    tipo = st.sidebar.selectbox("Seleziona STL", ["Dolomiti", "Belluno"])
    stl_data = stl_dolomiti if tipo == "Dolomiti" else stl_belluno

    if not stl_data.empty:
        st.header(f"🌄 STL {tipo} – Arrivi e Presenze mensili")
        anni_stl = sorted(stl_data["anno"].unique())
        anni_sel_stl = st.sidebar.multiselect("Anno (STL)", anni_stl, default=[anni_stl[-1]])
        stl_filtrata = stl_data[stl_data["anno"].isin(anni_sel_stl)]

        # Indicatori principali
        cols = st.columns(len(anni_sel_stl))
        for i, anno in enumerate(anni_sel_stl):
            tot_arr = int(stl_filtrata[stl_filtrata["anno"] == anno]["arrivi"].sum())
            tot_pre = int(stl_filtrata[stl_filtrata["anno"] == anno]["presenze"].sum())
            cols[i].metric(f"Arrivi {anno}", f"{tot_arr:,}".replace(",", "."))
            cols[i].metric(f"Presenze {anno}", f"{tot_pre:,}".replace(",", "."))

        # Grafici STL
        st.subheader("📈 Andamento Arrivi Mensili")
        fig_arrivi_stl = px.line(stl_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        st.plotly_chart(fig_arrivi_stl, use_container_width=True)

        st.subheader("📈 Andamento Presenze Mensili")
        fig_pres_stl = px.line(stl_filtrata, x="mese", y="presenze", color="anno", markers=True)
        st.plotly_chart(fig_pres_stl, use_container_width=True)

        # ======================
        # 📋 TABELLA CONFRONTO TRA ANNI (STL)
        # ======================
        st.subheader(f"📋 Confronto tra anni – Differenze e variazioni (STL {tipo})")

        if not stl_filtrata.empty:
            tabella_stl = (
                stl_filtrata.groupby(["anno", "mese"])[["arrivi", "presenze"]]
                .sum()
                .reset_index()
                .pivot_table(index="mese", columns="anno", values="presenze", fill_value=0)
            )

            # Aggiungi riga Totale
            totale = tabella_stl.sum(numeric_only=True)
            totale.name = "Totale Anno"
            tabella_stl = pd.concat([tabella_stl, totale.to_frame().T])

            # Se sono selezionati due anni → calcola differenze e variazioni
            if len(anni_sel_stl) == 2:
                anni_sorted = sorted(anni_sel_stl)
                anno_prev, anno_recent = anni_sorted
                tabella_stl["Differenza"] = tabella_stl[anno_recent] - tabella_stl[anno_prev]
                tabella_stl["Variazione %"] = (
                    (tabella_stl["Differenza"] / tabella_stl[anno_prev].replace(0, pd.NA)) * 100
                )

                st.markdown(
                    f"**Confronto tra {anno_recent} e {anno_prev}** – differenze e variazioni calcolate come *{anno_recent} − {anno_prev}*."
                )

                fmt = {col: "{:,.0f}".format for col in tabella_stl.columns if isinstance(col, int)}
                fmt.update({"Differenza": "{:,.0f}".format, "Variazione %": "{:.2f}%"})
                st.dataframe(tabella_stl.style.format(fmt, thousands="."))

            else:
                fmt = {col: "{:,.0f}".format for col in tabella_stl.columns if isinstance(col, int)}
                st.dataframe(tabella_stl.style.format(fmt, thousands="."))

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi – Uso interno")
