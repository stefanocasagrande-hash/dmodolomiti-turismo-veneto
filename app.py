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
# 📥 CARICAMENTO DATI COMUNALI
# ======================
st.sidebar.header("⚙️ Filtri principali")

data = load_data("dolomiti-turismo-veneto/dati-mensili-per-comune")

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
    data["anno"].isin(anno_sel)
    & data["comune"].isin(comune_sel)
    & data["mese"].isin(mesi_sel)
]

# ======================
# 🔢 INDICATORI PRINCIPALI COMUNALI
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
        xaxis=dict(categoryorder="array", categoryarray=mesi),
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
# 🏔️ TOGGLE PROVINCIA DI BELLUNO
# ======================
st.sidebar.markdown("---")
mostra_provincia = st.sidebar.checkbox("📍 Mostra dati Provincia di Belluno")

if mostra_provincia:
    st.markdown("---")
    st.header("🏔️ Provincia di Belluno – Arrivi e Presenze mensili")

    provincia = load_provincia_belluno("dolomiti-turismo-veneto/dati-provincia-annuali")

    if provincia.empty:
        st.warning("⚠️ Nessun dato provinciale caricato.")
    else:
        # Filtra per anni selezionati (se coincidono)
        provincia_filtrata = provincia[provincia["anno"].isin(anno_sel)] if "anno" in provincia.columns else provincia

        # ======================
        # 🔢 INDICATORI PROVINCIALI
        # ======================
        st.subheader("📈 Indicatori provincia Belluno")

        col1, col2 = st.columns(2)
        tot_arrivi = int(provincia_filtrata["arrivi"].sum())
        tot_presenze_prov = int(provincia_filtrata["presenze"].sum())

        col1.metric("Totale Arrivi", f"{tot_arrivi:,}".replace(",", "."))
        col2.metric("Totale Presenze", f"{tot_presenze_prov:,}".replace(",", "."))

        # ======================
        # 📊 GRAFICI PROVINCIALI
        # ======================
        col3, col4 = st.columns(2)

        with col3:
            fig_arrivi = px.line(
                provincia_filtrata,
                x="mese",
                y="arrivi",
                color="anno",
                markers=True,
                title="Andamento Arrivi mensili",
                labels={"arrivi": "Arrivi", "mese": "Mese"},
            )
            fig_arrivi.update_layout(legend_title_text="Anno")
            st.plotly_chart(fig_arrivi, use_container_width=True)

        with col4:
            fig_presenze = px.line(
                provincia_filtrata,
                x="mese",
                y="presenze",
                color="anno",
                markers=True,
                title="Andamento Presenze mensili",
                labels={"presenze": "Presenze", "mese": "Mese"},
            )
            fig_presenze.update_layout(legend_title_text="Anno")
            st.plotly_chart(fig_presenze, use_container_width=True)

        # ======================
        # 📋 TABELLA RIEPILOGATIVA
        # ======================
        st.subheader("📋 Riepilogo mensile – Provincia di Belluno")
        tabella = provincia_filtrata.pivot_table(
            index="mese",
            columns="anno",
            values=["arrivi", "presenze"],
            aggfunc="sum"
        ).round(0)
        st.dataframe(tabella)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Turismo Veneto – DMO Dolomiti. Tutti i diritti riservati.")
