import streamlit as st
import pandas as pd
import plotly.express as px
import tempfile
import pdfkit
import os

from etl import load_data, load_provincia_belluno

# ======================
# 🔐 AUTENTICAZIONE
# ======================
password = st.text_input("Inserisci password", type="password")
if password != "dolomiti":
    if password:
        st.error("❌ Password errata")
    st.stop()

# ======================
# 📥 CARICAMENTO DATI
# ======================
st.sidebar.header("⚙️ Filtri principali (Comuni)")
data = load_data("dati-mensili-per-comune")

if data.empty:
    st.error("❌ Nessun dato comunale caricato.")
    st.stop()

# ======================
# 📊 FILTRI COMUNALI
# ======================
anni = sorted(data["anno"].dropna().unique())
comuni = sorted(data["comune"].dropna().unique())
mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
        "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

anno_sel = st.sidebar.multiselect("Anno (Comuni)", anni, default=anni)
comune_sel = st.sidebar.multiselect("Comune", comuni, default=[comuni[0]])
mesi_sel = st.sidebar.multiselect("Mese", mesi, default=mesi)

# Filtraggio
df_filtered = data[
    data["anno"].isin(anno_sel) &
    data["comune"].isin(comune_sel) &
    data["mese"].isin(mesi_sel)
]

# ======================
# 📈 INDICATORI PRINCIPALI - COMUNI
# ======================
st.header("📈 Indicatori principali – Comuni")

if not df_filtered.empty:
    grouped = df_filtered.groupby(["comune", "anno"])["presenze"].sum().reset_index()
    for comune in grouped["comune"].unique():
        st.subheader(f"🏘️ {comune}")
        sub_df = grouped[grouped["comune"] == comune]
        for _, r in sub_df.iterrows():
            st.metric(f"{int(r['anno'])}", f"{r['presenze']:,.0f}".replace(",", "."))
else:
    st.info("Nessun dato disponibile per i filtri selezionati.")

# ======================
# 📊 ANDAMENTO MENSILE
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
    fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi),
                      legend_title_text="Anno")
    st.plotly_chart(fig, use_container_width=True)

# ======================
# 📊 CONFRONTO TRA MESI E ANNI
# ======================
st.subheader("📆 Confronto tra mesi nei diversi anni (Comuni)")

if not df_filtered.empty:
    fig_bar = px.bar(
        df_filtered,
        x="mese",
        y="presenze",
        color="anno",
        barmode="group",
        facet_row="comune"
    )
    fig_bar.update_layout(
        legend_title_text="Anno",
        bargap=0.2,
        bargroupgap=0.05,
        xaxis_title="Mese",
        yaxis_title="Presenze"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ======================
# 📋 CONFRONTO TRA ANNI E MESI – DIFFERENZE E VARIAZIONI
# ======================
st.subheader("📋 Confronto tra anni e mesi – Differenze e variazioni (Comuni)")

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
        with pd.option_context('mode.use_inf_as_na', True):
            tabella["Variazione %"] = (tabella["Differenza"] / tabella[anno_prev].replace(0, pd.NA)) * 100

        fmt = {col: "{:,.0f}".format for col in tabella.columns if isinstance(col, int)}
        fmt.update({"Differenza": "{:,.0f}".format, "Variazione %": "{:.2f}%"})
        st.markdown(f"**Confronto tra {anno_recent} e {anno_prev}:** calcolato come {anno_recent} − {anno_prev}.")
        st.dataframe(tabella.style.format(fmt, thousands="."))
    else:
        fmt = {col: "{:,.0f}".format for col in tabella.columns if isinstance(col, int)}
        st.dataframe(tabella.style.format(fmt, thousands="."))

# ======================
# 📍 DATI PROVINCIA DI BELLUNO
# ======================
show_prov = st.sidebar.toggle("📊 Mostra dati provincia di Belluno")

if show_prov:
    st.header("🏞 Dati Provincia di Belluno")
    data_provincia = load_provincia_belluno("dati-mensili-per-comune/dati-provincia-annuali")

    if not data_provincia.empty:
        anni_prov = sorted(data_provincia["anno"].unique())
        anni_prov_sel = st.sidebar.multiselect("Anno (Provincia)", anni_prov, default=anni_prov)
        df_prov = data_provincia[data_provincia["anno"].isin(anni_prov_sel)]

        # Grafico Arrivi
        st.subheader("🚶 Andamento arrivi mensili – Provincia Belluno")
        fig_arrivi = px.bar(
            df_prov, x="Mese", y="Totale arrivi", color="anno", barmode="group"
        )
        st.plotly_chart(fig_arrivi, use_container_width=True)

        # Grafico Presenze
        st.subheader("🛏 Andamento presenze mensili – Provincia Belluno")
        fig_pres = px.bar(
            df_prov, x="Mese", y="Totale presenze", color="anno", barmode="group"
        )
        st.plotly_chart(fig_pres, use_container_width=True)
    else:
        st.warning("⚠️ Nessun dato provinciale trovato.")

# ======================
# 📄 ESPORTAZIONE REPORT PDF
# ======================
st.sidebar.markdown("---")
st.sidebar.header("📄 Esporta Report in PDF")

def esporta_pdf(nome_file, sezioni_html):
    html = "<h1>Report Turismo Veneto</h1>" + "".join(sezioni_html)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
        tmp_html.write(html.encode("utf-8"))
        tmp_html.flush()
        pdf_path = tmp_html.name.replace(".html", ".pdf")
        try:
            pdfkit.from_file(tmp_html.name, pdf_path)
            with open(pdf_path, "rb") as f:
                st.sidebar.download_button(
                    label=f"💾 Scarica {nome_file}",
                    data=f,
                    file_name=nome_file,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Errore nella generazione PDF: {e}")

# ---- Pulsanti ----
if st.sidebar.button("📘 Report completo"):
    sezioni = [
        "<h2>Indicatori Comuni</h2>",
        df_filtered.to_html(index=False),
    ]
    if show_prov and 'data_provincia' in locals():
        sezioni.append("<h2>Dati Provincia Belluno</h2>")
        sezioni.append(data_provincia.to_html(index=False))
    esporta_pdf("report_turismo_completo.pdf", sezioni)

if st.sidebar.button("🏘 Solo Comuni"):
    sezioni = ["<h2>Dati Comuni</h2>", df_filtered.to_html(index=False)]
    esporta_pdf("report_comuni.pdf", sezioni)

if show_prov and st.sidebar.button("🏞 Solo Provincia Belluno"):
    sezioni = ["<h2>Dati Provincia Belluno</h2>", data_provincia.to_html(index=False)]
    esporta_pdf("report_provincia_belluno.pdf", sezioni)

