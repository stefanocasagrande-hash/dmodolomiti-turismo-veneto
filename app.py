import streamlit as st
import pandas as pd
import plotly.express as px
from etl import load_data, load_provincia_belluno

# ======================
# ⚙️ Configurazione iniziale
# ======================
st.set_page_config(page_title="Dashboard Turismo Veneto", layout="wide")
st.title("📊 Dashboard Turismo Veneto")

# ======================
# 🔐 Protezione con password
# ======================
password = st.text_input("Inserisci password", type="password")
if password != "veneto2025":
    if password:
        st.error("❌ Password errata. Riprova.")
    st.stop()
st.success("✅ Accesso consentito")

# ======================
# 📥 Caricamento dati
# ======================
st.sidebar.header("⚙️ Filtri principali")

data = load_data("dolomiti-turismo-veneto/dati-mensili-per-comune")
provincia = load_provincia_belluno("dolomiti-turismo-veneto/dati-provincia-annuali")

if data.empty:
    st.error("❌ Nessun dato comunale caricato.")
    st.stop()
else:
    st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")

if not provincia.empty:
    st.success(f"✅ Dati provinciali caricati: {len(provincia):,} righe, {provincia['anno'].nunique()} anni.")
else:
    st.warning("⚠️ Nessun dato provinciale disponibile.")

# ======================
# Filtri per dati comunali
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
# Indicatori principali (Comuni)
# ======================
st.header("📈 Indicatori principali - Comuni")

tot_presenze = df_filtered["presenze"].sum()
st.metric(label="Totale Presenze (filtrate)", value=f"{tot_presenze:,}".replace(",", "."))

# ======================
# Grafico andamento mensile (Comuni)
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
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# Grafico confronto mesi nei diversi anni (Comuni)
# ======================
st.subheader("📆 Confronto mesi nei diversi anni (Comuni)")

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
# Toggle e filtri per la sezione provinciale
# ======================
st.sidebar.markdown("---")
mostra_provincia = st.sidebar.checkbox("📍 Mostra dati Provincia di Belluno")

if mostra_provincia:
    st.markdown("---")
    st.header("🏔️ Provincia di Belluno – Arrivi e Presenze mensili")

    # Filtro separato per provincia (solo anno)
    anni_prov = sorted(provincia["anno"].unique())
    anno_sel_prov = st.selectbox("Seleziona anno (Provincia)", anni_prov, index=len(anni_prov)-1)

    prov_filtrata = provincia[provincia["anno"] == anno_sel_prov]

    if prov_filtrata.empty:
        st.warning("⚠️ Nessun dato provinciale per l'anno selezionato.")
    else:
        # Indicatori provinciali
        st.subheader("📈 Indicatori Provincia")
        tot_arrivi = int(prov_filtrata["arrivi"].sum())
        tot_pres = int(prov_filtrata["presenze"].sum())

        col1, col2 = st.columns(2)
        col1.metric("Totale Arrivi", f"{tot_arrivi:,}".replace(",", "."))
        col2.metric("Totale Presenze", f"{tot_pres:,}".replace(",", "."))

        # Se ci sono almeno 2 anni totali disponibili, calcola variazioni
        if len(anni_prov) >= 2:
            # trova l'altro anno per confronto
            other = [y for y in anni_prov if y != anno_sel_prov]
            if other:
                anno_prev = other[0]  # prendi il primo diverso
                prov_prev = provincia[provincia["anno"] == anno_prev]
                if not prov_prev.empty:
                    tot_pres_prev = int(prov_prev["presenze"].sum())
                    diff = tot_pres - tot_pres_prev
                    perc = (diff / tot_pres_prev) * 100 if tot_pres_prev != 0 else None
                    st.metric(
                        label=f"Variazione presenze {anno_prev} → {anno_sel_prov}",
                        value=f"{diff:+,}",
                        delta=f"{perc:.2f}%" if perc is not None else ""
                    )

        # Grafici province
        col3, col4 = st.columns(2)
        with col3:
            fig_arrivi = px.line(
                prov_filtrata,
                x="mese",
                y="arrivi",
                markers=True,
                title="Andamento Arrivi mensili",
                labels={"arrivi": "Arrivi", "mese": "Mese"}
            )
            st.plotly_chart(fig_arrivi, use_container_width=True)
        with col4:
            fig_pres = px.line(
                prov_filtrata,
                x="mese",
                y="presenze",
                markers=True,
                title="Andamento Presenze mensili",
                labels={"presenze": "Presenze", "mese": "Mese"}
            )
            st.plotly_chart(fig_pres, use_container_width=True)

        # Tabella riepilogativa mensile
        st.subheader("📋 Riepilogo mensile provincia")
        st.dataframe(
            prov_filtrata.pivot_table(
                index="mese",
                values=["arrivi", "presenze"],
                aggfunc="sum"
            ).round(0)
        )

# ======================
# 🧾 Footer
# ======================
st.caption("© 2025 Dashboard Turismo Veneto – DMO Dolomiti. Tutti i diritti riservati.")

