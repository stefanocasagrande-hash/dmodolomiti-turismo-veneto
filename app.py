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
        fmt.update({
            "Differenza": "{:,.0f}".format,
            "Variazione %": "{:.2f}%"
        })

        st.markdown(f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come {anno_recent} − {anno_prev}.")
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

        prov_filtrata = provincia[provincia["anno"].isin(anni_sel_prov)].copy()

        if prov_filtrata.empty:
            st.warning("❌ Nessun dato provinciale per gli anni selezionati.")
        else:
            # Normalizzazione mese
            prov_filtrata["mese"] = prov_filtrata["mese"].str.strip().str[:3].str.capitalize()
            prov_filtrata["mese"] = pd.Categorical(prov_filtrata["mese"], categories=mesi, ordered=True)

            # === GRAFICO ARRIVI A LINEE ===
            st.subheader("🚶 Andamento mensile – Arrivi")
            fig_arr = px.line(
                prov_filtrata,
                x="mese",
                y="arrivi",
                color="anno",
                markers=True,
                title="Arrivi mensili per anno – Provincia Belluno",
                labels={"arrivi": "Arrivi", "mese": "Mese", "anno": "Anno"}
            )
            fig_arr.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
            st.plotly_chart(fig_arr, use_container_width=True)

            # === GRAFICO PRESENZE A LINEE ===
            st.subheader("🛏 Andamento mensile – Presenze")
            fig_pres = px.line(
                prov_filtrata,
                x="mese",
                y="presenze",
                color="anno",
                markers=True,
                title="Presenze mensili per anno – Provincia Belluno",
                labels={"presenze": "Presenze", "mese": "Mese", "anno": "Anno"}
            )
            fig_pres.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi))
            st.plotly_chart(fig_pres, use_container_width=True)

            # === TABELLA RIEPILOGO PROVINCIA ===
            st.subheader("📋 Riepilogo mensile – Provincia di Belluno")
            tabella_prov = prov_filtrata.pivot_table(
                index="mese",
                columns="anno",
                values=["arrivi", "presenze"],
                aggfunc="sum"
            ).round(0)

            if len(anni_sel_prov) == 2:
                anni_sorted_prov = sorted(anni_sel_prov)
                anno_prev_prov = anni_sorted_prov[0]
                anno_recent_prov = anni_sorted_prov[1]
                for metrica in ["arrivi", "presenze"]:
                    diff_col = (metrica, "Differenza")
                    pct_col = (metrica, "Variazione %")
                    tabella_prov[diff_col] = tabella_prov[(metrica, anno_recent_prov)] - tabella_prov[(metrica, anno_prev_prov)]
                    with pd.option_context('mode.use_inf_as_na', True):
                        tabella_prov[pct_col] = (tabella_prov[diff_col] / tabella_prov[(metrica, anno_prev_prov)].replace(0, pd.NA)) * 100

                st.markdown(
                    f"**Confronto tra {anno_recent_prov} e {anno_prev_prov}:** differenze e variazioni calcolate come {anno_recent_prov} − {anno_prev_prov}."
                )

            fmt = {col: "{:,.0f}".format for col in tabella_prov.columns if not (isinstance(col, tuple) and col[1] == 'Variazione %')}
            fmt.update({col: "{:.2f}%" for col in tabella_prov.columns if isinstance(col, tuple) and col[1] == 'Variazione %'})
            st.dataframe(tabella_prov.style.format(fmt, thousands="."))


# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi - Per uso interno - Tutti i diritti riservati.")

