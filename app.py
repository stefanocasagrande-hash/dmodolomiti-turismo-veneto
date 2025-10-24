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
st.header("📈 Analisi Presenze – Comuni")
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
    st.subheader("📈 Andamento mensile Presenze (Comuni)")
    fig = px.line(df_filtered, x="mese", y="presenze", color="anno", markers=True, facet_row="comune")
    fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 📋 TABELLA CONFRONTO TRA ANNI E MESI – COMUNI
# ======================
st.subheader("📊 Confronto tra anni e mesi – Differenze e variazioni Presenze (Comuni)")

if not df_filtered.empty:
    tabella_com = (
        df_filtered.groupby(["anno", "mese"])["presenze"]
        .sum()
        .reset_index()
        .pivot_table(index="mese", columns="anno", values="presenze", fill_value=0)
    )

    # Ordina mesi
    mesi_ordine = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    tabella_com = tabella_com.reindex(mesi_ordine)

    # Aggiungi riga Totale
    totale = pd.DataFrame(tabella_com.sum()).T
    totale.index = ["Totale"]
    tabella_com = pd.concat([tabella_com, totale])

    # Se due anni selezionati → aggiungi differenze e variazioni %
    if len(anno_sel) == 2:
        anni_sorted = sorted(anno_sel)
        anno_prev, anno_recent = anni_sorted

        tabella_com["Differenza"] = tabella_com[anno_recent] - tabella_com[anno_prev]
        tabella_com["Variazione %"] = (tabella_com["Differenza"] / tabella_com[anno_prev].replace(0, pd.NA)) * 100

        st.markdown(
            f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come *{anno_recent} − {anno_prev}*."
        )

        def color_var(val):
            if pd.isna(val):
                return "color: grey;"
            elif val > 0:
                return "color: green; font-weight: bold;"
            elif val < 0:
                return "color: red; font-weight: bold;"
            else:
                return "color: grey;"

        fmt = {}
        for col in tabella_com.columns:
            if col == "Variazione %":
                fmt[col] = "{:.2f}%"
            else:
                fmt[col] = "{:,.0f}".format

        styled = (
            tabella_com.style.format(fmt, thousands=".")
            .applymap(color_var, subset=["Variazione %"])
        )

        st.dataframe(styled, use_container_width=True)
    else:
        fmt = {col: "{:,.0f}".format for col in tabella_com.columns if tabella_com[col].dtype != "O"}
        st.dataframe(tabella_com.style.format(fmt, thousands="."), use_container_width=True)
else:
    st.info("Nessun dato disponibile per creare la tabella di confronto.")

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
        sel_metrica = st.sidebar.radio("Seleziona metrica", ("Presenze", "Arrivi"))

        stl_filtrata = stl_data[stl_data["anno"].isin(anni_sel_stl)].copy()
        # Rimuovi eventuali righe "Totale"
        stl_filtrata["mese"] = stl_filtrata["mese"].astype(str).str.strip()
        stl_filtrata = stl_filtrata[~stl_filtrata["mese"].str.lower().str.contains(r"^tot")]

        # Ordina mesi da Gen a Dic
        mesi_validi = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
        stl_filtrata["mese"] = pd.Categorical(stl_filtrata["mese"], categories=mesi_validi, ordered=True)
        stl_filtrata = stl_filtrata.sort_values(["anno","mese"])

        # ======================
        # 📈 INDICATORI PRINCIPALI
        # ======================
        cols = st.columns(len(anni_sel_stl))
        for i, anno in enumerate(anni_sel_stl):
            tot_val = int(stl_filtrata[stl_filtrata["anno"] == anno][sel_metrica.lower()].sum())
            cols[i].metric(f"{sel_metrica} {anno}", f"{tot_val:,}".replace(",", "."))

        # ======================
        # 📊 VARIAZIONE % IN ALTO (KPI)
        # ======================
        if len(anni_sel_stl) == 2:
            anno_prev, anno_recent = sorted(anni_sel_stl)
            stl_prev = stl_filtrata[stl_filtrata["anno"] == anno_prev]
            stl_recent = stl_filtrata[stl_filtrata["anno"] == anno_recent]

            tot_pres_prev = stl_prev["presenze"].sum()
            tot_pres_recent = stl_recent["presenze"].sum()
            tot_arr_prev = stl_prev["arrivi"].sum()
            tot_arr_recent = stl_recent["arrivi"].sum()

            var_pres = ((tot_pres_recent - tot_pres_prev) / tot_pres_prev * 100) if tot_pres_prev else 0
            var_arr = ((tot_arr_recent - tot_arr_prev) / tot_arr_prev * 100) if tot_arr_prev else 0

            st.markdown("### 🔼 Variazioni complessive tra gli anni selezionati")
            c1, c2 = st.columns(2)

            color_pres = "green" if var_pres > 0 else ("red" if var_pres < 0 else "grey")
            color_arr = "green" if var_arr > 0 else ("red" if var_arr < 0 else "grey")

            c1.markdown(
                f"<div style='font-size:20px;'><b>Presenze</b> {anno_recent} vs {anno_prev}: "
                f"<span style='color:{color_pres};'>{var_pres:+.2f}%</span></div>",
                unsafe_allow_html=True
            )
            c2.markdown(
                f"<div style='font-size:20px;'><b>Arrivi</b> {anno_recent} vs {anno_prev}: "
                f"<span style='color:{color_arr};'>{var_arr:+.2f}%</span></div>",
                unsafe_allow_html=True
            )

        # ======================
        # 📈 GRAFICI STL
        # ======================
        st.subheader("📈 Andamento Arrivi Mensili")
        fig_arr = px.line(stl_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        fig_arr.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi_validi))
        st.plotly_chart(fig_arr, use_container_width=True)

        st.subheader("📈 Andamento Presenze Mensili")
        fig_pre = px.line(stl_filtrata, x="mese", y="presenze", color="anno", markers=True)
        fig_pre.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi_validi))
        st.plotly_chart(fig_pre, use_container_width=True)

        # ======================
# 📊 TABELLA CONFRONTO TRA ANNI E MESI (STL)
# ======================
st.subheader(f"📊 Confronto tra anni e mesi – Differenze e variazioni (STL {sel_metrica})")

# Usa la metrica selezionata (arrivi o presenze)
colonna = sel_metrica.lower()

tabella_stl = (
    stl_filtrata.groupby(["anno", "mese"])[colonna]
    .sum()
    .reset_index()
    .pivot_table(index="mese", columns="anno", values=colonna, fill_value=0)
)

# Ordina mesi
mesi_ordine = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
tabella_stl = tabella_stl.reindex(mesi_ordine)

# Aggiungi riga Totale
totale = pd.DataFrame(tabella_stl.sum()).T
totale.index = ["Totale"]
tabella_stl = pd.concat([tabella_stl, totale])

# Se due anni selezionati → calcola differenze e variazioni %
if len(anni_sel_stl) == 2:
    anno_prev, anno_recent = sorted(anni_sel_stl)

    tabella_stl["Differenza"] = tabella_stl[anno_recent] - tabella_stl[anno_prev]
    tabella_stl["Variazione %"] = (tabella_stl["Differenza"] / tabella_stl[anno_prev].replace(0, pd.NA)) * 100

    st.markdown(
        f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come *{anno_recent} − {anno_prev}*."
    )

    def color_var(val):
        if pd.isna(val):
            return "color: grey;"
        elif val > 0:
            return "color: green; font-weight: bold;"
        elif val < 0:
            return "color: red; font-weight: bold;"
        else:
            return "color: grey;"

    fmt = {}
    for col in tabella_stl.columns:
        if col == "Variazione %":
            fmt[col] = "{:.2f}%"
        else:
            fmt[col] = "{:,.0f}".format

    styled = (
        tabella_stl.style.format(fmt, thousands=".")
        .applymap(color_var, subset=["Variazione %"])
    )

    st.dataframe(styled, use_container_width=True)
else:
    fmt = {col: "{:,.0f}".format for col in tabella_stl.columns if tabella_stl[col].dtype != "O"}
    st.dataframe(tabella_stl.style.format(fmt, thousands="."), use_container_width=True)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi – Uso interno")
