import os, sys
print("DEBUG current working dir:", os.getcwd())
print("DEBUG files in cwd:", os.listdir("."))
print("DEBUG sys.path:", sys.path[:5])

import streamlit as st
import pandas as pd
import plotly.express as px
from etl import load_data, load_provincia_belluno

# --- DEBUG TEMPORANEO: rimuovere dopo i controlli ---
import os, sys
st.write("DEBUG: working dir:", os.getcwd())
st.write("DEBUG: __file__ (app):", __file__ if "__file__" in globals() else "n/a")
st.write("DEBUG: python sys.path:", sys.path[:5])
root_list = sorted(os.listdir(".")) if os.path.exists(".") else []
st.write("DEBUG: root listing (first 40):", root_list[:40])
target = os.path.join(os.getcwd(), "dati-mensili-per-comune")
st.write("DEBUG: target path exist:", os.path.exists(target), " ->", target)
if os.path.exists(target):
    files = sorted([f for f in os.listdir(target) if f.lower().endswith((".txt",".csv"))])
    st.write("DEBUG: files in target (count):", len(files))
    st.write("DEBUG: files sample:", files[:10])
    if files:
        sample = os.path.join(target, files[0])
        try:
            with open(sample, "rb") as fh:
                raw = fh.read(800)
            st.write("DEBUG: first bytes of", files[0], ":", raw[:800])
        except Exception as e:
            st.write("DEBUG: impossibile leggere sample:", e)
# --- fine debug ---

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

data = load_dati_comunali("dolomiti-turismo-veneto/dati-mensili-per-comune")
provincia = load_provincia_belluno("dolomiti-turismo-veneto/dati-provincia-annuali")
stl_dolomiti, stl_belluno = load_stl_data("dolomiti-turismo-veneto/stl-presenze-arrivi")

# ======================
# ✅ VERIFICA CARICAMENTO
# ======================
if data.empty:
    st.error("❌ Nessun dato comunale caricato. Controlla la cartella 'dati-mensili-per-comune'.")
    st.stop()
else:
    st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")

if not provincia.empty:
    st.success(f"✅ Dati provinciali caricati: {len(provincia):,} righe, {provincia['anno'].nunique()} anni.")
if not stl_dolomiti.empty or not stl_belluno.empty:
    st.success("✅ Dati STL caricati correttamente.")

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

        st.markdown(
            f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come {anno_recent} − {anno_prev}."
        )
        st.dataframe(tabella.style.format(fmt, thousands="."))
    else:
        fmt = {col: "{:,.0f}".format for col in tabella.columns if isinstance(col, int)}
        st.dataframe(tabella.style.format(fmt, thousands="."))
else:
    st.info("Seleziona almeno un anno e un comune per visualizzare la tabella comparativa.")

# ======================
# 📊 GRAFICO ANDAMENTO MENSILE (Comuni)
# ======================
st.subheader("📊 Andamento mensile (Comuni)")

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
        xaxis=dict(categoryorder="array", categoryarray=mesi),
        legend_title_text="Anno"
    )
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 📊 CONFRONTO TRA MESI NEI DIVERSI ANNI (Comuni)
# ======================
st.subheader("📆 Confronto tra mesi nei diversi anni (Comuni)")

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
            tot_arrivi = int(prov_annuale["arrivi"].sum()) if not prov_annuale.empty else 0
            tot_pres = int(prov_annuale["presenze"].sum()) if not prov_annuale.empty else 0
            cols_metric[i].metric(f"Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            cols_metric[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        # Grafici lineari
        st.subheader("📈 Andamento Arrivi Mensili")
        fig_arrivi = px.line(prov_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        st.plotly_chart(fig_arrivi, use_container_width=True)

        st.subheader("📈 Andamento Presenze Mensili")
        fig_pres = px.line(prov_filtrata, x="mese", y="presenze", color="anno", markers=True)
        st.plotly_chart(fig_pres, use_container_width=True)

# ======================
# 🏔️ SEZIONE STL
# ======================
st.sidebar.markdown("---")
mostra_stl = st.sidebar.checkbox("📍 Mostra dati STL (Dolomiti / Belluno)")

if mostra_stl:
    st.sidebar.header("⚙️ Filtri – Dati STL")

    stl_tipo = st.sidebar.selectbox("Seleziona STL", ["Dolomiti", "Belluno"])
    stl_data = stl_dolomiti if stl_tipo == "Dolomiti" else stl_belluno

    if stl_data.empty:
        st.warning(f"⚠️ Nessun dato STL {stl_tipo} caricato.")
    else:
        anni_stl = sorted(stl_data["anno"].unique())
        anni_sel_stl = st.sidebar.multiselect("Seleziona Anno (STL)", anni_stl, default=[anni_stl[-1]])

        st.markdown("---")
        st.header(f"🏔️ STL {stl_tipo} – Arrivi e Presenze mensili")

        stl_filtrata = stl_data[stl_data["anno"].isin(anni_sel_stl)]

        # Indicatori STL
        st.subheader("📈 Indicatori STL")
        cols_metric = st.columns(len(anni_sel_stl))
        for i, anno in enumerate(anni_sel_stl):
            stl_annuale = stl_filtrata[stl_filtrata["anno"] == anno]
            tot_arrivi = int(stl_annuale["arrivi"].sum())
            tot_pres = int(stl_annuale["presenze"].sum())
            cols_metric[i].metric(f"Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            cols_metric[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        # Grafici STL
        st.subheader("📈 Andamento Arrivi Mensili")
        fig_arrivi_stl = px.line(stl_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        st.plotly_chart(fig_arrivi_stl, use_container_width=True)

        st.subheader("📈 Andamento Presenze Mensili")
        fig_pres_stl = px.line(stl_filtrata, x="mese", y="presenze", color="anno", markers=True)
        st.plotly_chart(fig_pres_stl, use_container_width=True)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")
