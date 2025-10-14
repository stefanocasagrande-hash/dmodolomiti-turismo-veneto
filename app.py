import streamlit as st
import os
import pandas as pd
import plotly.express as px
from etl import load_data, load_provincia_belluno

# ======================
# 🔐 LOGIN SEMPLICE
# ======================
st.set_page_config(page_title="Turismo Veneto - Dashboard", layout="wide")

st.title("📊 Turismo Veneto - Dashboard Interattiva")

password = st.text_input("Inserisci password per accedere:", type="password")

if password != "segreta123":
    if password:
        st.error("❌ Password errata. Riprova.")
    st.stop()

st.success("✅ Accesso consentito")

# ======================
# 🔄 CARICAMENTO DATI
# ======================
st.markdown("### 📦 Caricamento dati...")

data = load_data()
provincia = load_provincia_belluno()

if data.empty:
    st.error("❌ Nessun dato comunale trovato.")
    st.stop()
else:
    st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")

if provincia.empty:
    st.warning("⚠️ Nessun dato provinciale trovato.")
else:
    st.success(f"✅ Dati provinciali caricati: {len(provincia):,} righe, {provincia['anno'].nunique()} anni.")

# ======================
# 🔍 FILTRI
# ======================
st.sidebar.header("🎚️ Filtri")

anni = sorted(data["anno"].unique())
comuni = sorted(data["comune"].unique())

anno_sel = st.sidebar.multiselect("Seleziona anni", anni, default=anni)
comune_sel = st.sidebar.multiselect("Seleziona Comuni", comuni, default=["Belluno"])

data_filtrata = data[data["anno"].isin(anno_sel) & data["comune"].isin(comune_sel)]

# ======================
# 🔢 INDICATORI PRINCIPALI
# ======================
st.markdown("## 📈 Indicatori principali")

col1, col2 = st.columns(2)
for comune in comune_sel:
    df_comune = data_filtrata[data_filtrata["comune"] == comune]
    with col1:
        st.markdown(f"### 🏙️ {comune}")
    with col2:
        for anno in anno_sel:
            tot_presenze = int(df_comune[df_comune["anno"] == anno]["presenze"].sum())
            st.metric(label=f"Presenze totali {anno}", value=f"{tot_presenze:,}")

if len(anno_sel) == 2:
    anno1, anno2 = anno_sel
    df_diff = data_filtrata[data_filtrata["anno"].isin([anno1, anno2])]
    diff = (
        df_diff[df_diff["anno"] == anno2]["presenze"].sum()
        - df_diff[df_diff["anno"] == anno1]["presenze"].sum()
    )
    perc = (diff / df_diff[df_diff["anno"] == anno1]["presenze"].sum()) * 100
    st.metric(label=f"Variazione {anno1}→{anno2}", value=f"{diff:+,}", delta=f"{perc:.2f}%")

# ======================
# 📊 GRAFICO: ANDAMENTO MENSILE
# ======================
st.markdown("## 📅 Andamento mensile")

if data_filtrata.empty:
    st.warning("Nessun dato disponibile per i filtri selezionati.")
else:
    fig = px.bar(
        data_filtrata,
        x="mese",
        y="presenze",
        color="anno",
        barmode="group",
        facet_col="comune" if len(comune_sel) > 1 else None,
        title="Confronto presenze mensili per anno e comune",
        labels={"presenze": "Presenze", "mese": "Mese", "anno": "Anno"},
    )
    fig.update_layout(legend_title_text="Anno", legend_orientation="h", legend_y=-0.2)
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 📋 TABELLA DETTAGLIO
# ======================
st.markdown("## 📋 Tabella presenze filtrate")

tabella = (
    data_filtrata.groupby(["anno", "comune"])["presenze"]
    .sum()
    .reset_index()
    .pivot(index="comune", columns="anno", values="presenze")
    .fillna(0)
)

if len(anno_sel) == 2:
    anno1, anno2 = anno_sel
    tabella["Differenza assoluta"] = tabella[anno2] - tabella[anno1]
    tabella["Differenza %"] = ((tabella[anno2] - tabella[anno1]) / tabella[anno1]) * 100

st.dataframe(tabella.style.format({"Differenza %": "{:.2f}%"}))

# ======================
# 🏔️ SEZIONE PROVINCIA DI BELLUNO
# ======================
st.markdown("## 🏔️ Provincia di Belluno – Arrivi e Presenze per mese")

if not provincia.empty:
    col1, col2 = st.columns(2)

    with col1:
        fig_arrivi = px.bar(
            provincia,
            x="mese",
            y="arrivi",
            color="anno",
            barmode="group",
            title="Arrivi mensili – Provincia di Belluno",
            labels={"arrivi": "Arrivi", "mese": "Mese"},
        )
        st.plotly_chart(fig_arrivi, use_container_width=True)

    with col2:
        fig_presenze = px.bar(
            provincia,
            x="mese",
            y="presenze",
            color="anno",
            barmode="group",
            title="Presenze mensili – Provincia di Belluno",
            labels={"presenze": "Presenze", "mese": "Mese"},
        )
        st.plotly_chart(fig_presenze, use_container_width=True)

else:
    st.warning("⚠️ Nessun dato provinciale disponibile.")

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Turismo Veneto – DMO Dolomiti. Tutti i diritti riservati.")
