import streamlit as st
import pandas as pd
import plotly.express as px
from etl import load_data, load_provincia_belluno

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

data = load_data("dolomiti-turismo-veneto/dati-mensili-per-comune")
provincia = load_provincia_belluno("dolomiti-turismo-veneto/dati-provincia-annuali")

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

if len(anno_sel) >= 1 and not df_filtered.empty:
    tabella = (
        df_filtered.groupby(["anno", "comune", "mese"])["presenze"]
        .sum()
        .reset_index()
        .pivot_table(index=["comune", "mese"], columns="anno", values="presenze", fill_value=0)
    )

    if len(anno_sel) >= 2:
        # Calcolo tra anno più recente (maggiore) e anno precedente (minore)
        anni_sorted = sorted(anno_sel)
        anno_recent = anni_sorted[-1]   # es. 2024
        anno_prev = anni_sorted[0]      # es. 2023

        tabella["Differenza"] = tabella.get(anno_recent, 0) - tabella.get(anno_prev, 0)
        with pd.option_context('mode.use_inf_as_na', True):
            tabella["Variazione %"] = (tabella["Differenza"] / tabella[anno_prev].replace(0, pd.NA)) * 100

        # Formattazione leggibile
        fmt = {
            anno_recent: "{:,.0f}".format,
            anno_prev: "{:,.0f}".format,
            "Differenza": "{:,.0f}".format,
            "Variazione %": "{:.2f}%"
        }

        st.dataframe(
            tabella.style.format(fmt, thousands=".")
        )

    else:
        # Se un solo anno, formatta comunque i numeri con separatore
        st.dataframe(
            tabella.style.format("{:,.0f}", thousands=".")
        )

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
        anni_sel_prov = st.sidebar.multiselect(
            "Seleziona Anno (Provincia)",
            anni_prov,
            default=[anni_prov[-1]]
        )

        st.markdown("---")
        st.header("🏔️ Provincia di Belluno – Arrivi e Presenze mensili")

        prov_filtrata = provincia[provincia["anno"].isin(anni_sel_prov)]

        # Indicatori Provincia
        st.subheader("📈 Indicatori Provincia di Belluno")
        cols_metric = st.columns(len(anni_sel_prov))
        for i, anno in enumerate(anni_sel_prov):
            prov_annuale = prov_filtrata[prov_filtrata["anno"] == anno]
            tot_arrivi = int(prov_annuale["arrivi"].sum()) if not prov_annuale.empty else 0
            tot_pres = int(prov_annuale["presenze"].sum()) if not prov_annuale.empty else 0
            cols_metric[i].metric(f"Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            cols_metric[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        # Seleziona gli anni più grande e più piccolo tra quelli scelti
        if len(anni_sel_prov) >= 2:
            anni_sorted_prov = sorted(anni_sel_prov)
            anno_prev_prov = anni_sorted_prov[0]   # meno recente
            anno_recent_prov = anni_sorted_prov[-1]  # più recente
        else:
            anno_prev_prov = None
            anno_recent_prov = None

        # Grafici – confronto anni
        st.subheader("📊 Andamento mensile – Arrivi e Presenze (confronto anni)")
        col3, col4 = st.columns(2)

        with col3:
            fig_arrivi = px.line(
                prov_filtrata,
                x="mese",
                y="arrivi",
                color="anno",
                markers=True,
                title="Andamento Arrivi mensili",
                labels={"arrivi": "Arrivi", "mese": "Mese", "anno": "Anno"}
            )
            fig_arrivi.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
            st.plotly_chart(fig_arrivi, use_container_width=True)

        with col4:
            fig_pres = px.line(
                prov_filtrata,
                x="mese",
                y="presenze",
                color="anno",
                markers=True,
                title="Andamento Presenze mensili",
                labels={"presenze": "Presenze", "mese": "Mese", "anno": "Anno"}
            )
            fig_pres.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
            st.plotly_chart(fig_pres, use_container_width=True)

        # Tabella riepilogo e confronto
        st.subheader("📋 Riepilogo mensile – Provincia di Belluno")

        tabella_prov = prov_filtrata.pivot_table(
            index="mese",
            columns="anno",
            values=["arrivi", "presenze"],
            aggfunc="sum"
        ).round(0)

        if anno_prev_prov and anno_recent_prov:
            for metrica in ["arrivi", "presenze"]:
                recent_col = (metrica, anno_recent_prov)
                prev_col = (metrica, anno_prev_prov)
                if recent_col in tabella_prov.columns and prev_col in tabella_prov.columns:
                    diff_col = (metrica, "Differenza")
                    pct_col = (metrica, "Variazione %")
                    tabella_prov[diff_col] = tabella_prov[recent_col] - tabella_prov[prev_col]
                    with pd.option_context('mode.use_inf_as_na', True):
                        tabella_prov[pct_col] = (tabella_prov[diff_col] / tabella_prov[prev_col].replace(0, pd.NA)) * 100

        fmt = {col: "{:.2f}%" for col in tabella_prov.columns if isinstance(col, tuple) and col[1] == "Variazione %"}
        st.dataframe(tabella_prov.style.format(fmt))

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Turismo Veneto – DMO Dolomiti. Tutti i diritti riservati.")

