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
if password != "segreta123":
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
        col_comm = st.columns(len(anno_sel))
        for i, anno in enumerate(anno_sel):
            tot_pres = int(df_filtered[(df_filtered["anno"] == anno) & (df_filtered["comune"] == comune)]["presenze"].sum())
            col_comm[i].metric(f"Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

# ======================
# 📋 TABELLA CONFRONTO TRA ANNI E MESI
# ======================
st.subheader("📊 Confronto tra anni e mesi – Differenze e variazioni")

if len(anno_sel) >= 1 and not df_filtered.empty:
    tabella = (
        df_filtered.groupby(["anno", "comune", "mese"])["presenze"]
        .sum()
        .reset_index()
        .pivot_table(index=["comune", "mese"], columns="anno", values="presenze", fill_value=0)
    )

    if len(anno_sel) == 2:
        anno1, anno2 = anno_sel
        tabella["Differenza"] = tabella[anno2] - tabella[anno1]
        tabella["Variazione %"] = ((tabella[anno2] - tabella[anno1]) / tabella[anno1].replace(0, pd.NA)) * 100
        st.dataframe(tabella.style.format({"Variazione %": "{:.2f}%"}))
    else:
        st.dataframe(tabella)
else:
    st.info("Seleziona almeno un anno per visualizzare la tabella comparativa.")

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

        # Indicatori
        st.subheader("📈 Indicatori Provincia di Belluno")
        for anno in anni_sel_prov:
            prov_annuale = prov_filtrata[prov_filtrata["anno"] == anno]
            col1, col2 = st.columns(2)
            tot_arrivi = int(prov_annuale["arrivi"].sum())
            tot_pres = int(prov_annuale["presenze"].sum())
            col1.metric(f"Totale Arrivi {anno}", f"{tot_arrivi:,}".replace(",", "."))
            col2.metric(f"Totale Presenze {anno}", f"{tot_pres:,}".replace(",", "."))

        # Grafici – confronto tra anni
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

        # Tabella riepilogo
        st.subheader("📋 Riepilogo mensile – Provincia di Belluno")
        tabella_prov = prov_filtrata.pivot_table(
            index=["mese"],
            columns="anno",
            values=["arrivi", "presenze"],
            aggfunc="sum"
        ).round(0)
        st.dataframe(tabella_prov)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Turismo Veneto – DMO Dolomiti. Tutti i diritti riservati.")
