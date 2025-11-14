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

        # Filtri anni
        anni_prov = sorted(provincia["anno"].unique())
        anni_sel_prov = st.sidebar.multiselect("Anno (Provincia)", anni_prov, default=[anni_prov[-1]])

        # Filtra dati e rimuovi righe "Totale"
        prov_filtrata = provincia[provincia["anno"].isin(anni_sel_prov)].copy()
        prov_filtrata["mese"] = prov_filtrata["mese"].astype(str).str.strip()
        prov_filtrata = prov_filtrata[~prov_filtrata["mese"].str.lower().str.contains(r"^tot")]

        # Ordina mesi in ordine cronologico
        mesi_ordine = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        prov_filtrata["mese"] = pd.Categorical(prov_filtrata["mese"].str[:3].str.capitalize(), categories=mesi_ordine, ordered=True)
        prov_filtrata = prov_filtrata.sort_values(["anno", "mese"])

        # ======================
        # 📈 INDICATORI PRINCIPALI
        # ======================
        st.subheader("📈 Indicatori Provincia di Belluno")
        cols = st.columns(len(anni_sel_prov))
        for i, anno in enumerate(anni_sel_prov):
            dati_anno = prov_filtrata[prov_filtrata["anno"] == anno]
            tot_arr = int(dati_anno["arrivi"].sum())
            tot_pre = int(dati_anno["presenze"].sum())
            cols[i].metric(f"Arrivi {anno}", f"{tot_arr:,}".replace(",", "."))
            cols[i].metric(f"Presenze {anno}", f"{tot_pre:,}".replace(",", "."))

        # ======================
        # 📊 GRAFICI ANDAMENTO MENSILE
        # ======================
        st.subheader("📈 Andamento Arrivi Mensili")
        fig_arr = px.line(prov_filtrata, x="mese", y="arrivi", color="anno", markers=True)
        fig_arr.update_layout(
            xaxis=dict(categoryorder="array", categoryarray=mesi_ordine),
            legend_title_text="Anno"
        )
        st.plotly_chart(fig_arr, use_container_width=True)

        st.subheader("📈 Andamento Presenze Mensili")
        fig_pre = px.line(prov_filtrata, x="mese", y="presenze", color="anno", markers=True)
        fig_pre.update_layout(
            xaxis=dict(categoryorder="array", categoryarray=mesi_ordine),
            legend_title_text="Anno"
        )
        st.plotly_chart(fig_pre, use_container_width=True)

        # ======================
        # 📋 TABELLA CONFRONTO TRA ANNI E MESI (Provincia di Belluno)
        # ======================
        st.subheader("📊 Confronto tra anni e mesi – Differenze e variazioni (Provincia)")

        tab_prov = (
            prov_filtrata.groupby(["anno", "mese"])[["arrivi", "presenze"]]
            .sum()
            .reset_index()
        )

        # Pivot per tabella comparativa
        tabella_prov = tab_prov.pivot_table(index="mese", columns="anno", values=["arrivi", "presenze"], fill_value=0)

        # Aggiungi riga Totale
        totale = pd.DataFrame(tabella_prov.sum()).T
        totale.index = ["Totale"]
        tabella_prov = pd.concat([tabella_prov, totale])

        # Se due anni selezionati → differenze e variazioni %
        if len(anni_sel_prov) == 2:
            anno_prev, anno_recent = sorted(anni_sel_prov)
            for met in ["arrivi", "presenze"]:
                tabella_prov[(met, "Differenza")] = tabella_prov[(met, anno_recent)] - tabella_prov[(met, anno_prev)]
                tabella_prov[(met, "Variazione %")] = (
                    (tabella_prov[(met, "Differenza")] /
                     tabella_prov[(met, anno_prev)].replace(0, pd.NA)) * 100
                )

            st.markdown(
                f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come *{anno_recent} − {anno_prev}*."
            )

            # Formattazione e colori
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
            for col in tabella_prov.columns:
                if col[1] == "Variazione %":
                    fmt[col] = "{:.2f}%"
                else:
                    fmt[col] = "{:,.0f}".format

            styled = (
                tabella_prov.style.format(fmt, thousands=".")
                .applymap(color_var, subset=[c for c in tabella_prov.columns if c[1] == "Variazione %"])
            )
            st.dataframe(styled, use_container_width=True)
        else:
            fmt = {col: "{:,.0f}".format for col in tabella_prov.columns}
            st.dataframe(tabella_prov.style.format(fmt, thousands="."), use_container_width=True)

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

        # Pulizia e ordinamento dati
        stl_filtrata = stl_data[stl_data["anno"].isin(anni_sel_stl)].copy()
        stl_filtrata["mese"] = stl_filtrata["mese"].astype(str).str.strip()
        stl_filtrata = stl_filtrata[~stl_filtrata["mese"].str.lower().str.contains(r"^tot")]

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
        # 📊 VARIAZIONE % COMPLESSIVA (considera solo i mesi con valore > 0 nell'anno più recente)
        # ======================
        if len(anni_sel_stl) == 2:
            anno_prev, anno_recent = sorted(anni_sel_stl)

            # metrica selezionata (arrivi o presenze)
            metr = sel_metrica.lower()

            # Prendi i mesi dell'anno recente che hanno valore > 0 (cioè mesi con dati reali)
            recent_months = (
                stl_filtrata.loc[stl_filtrata["anno"] == anno_recent, ["mese", metr]]
                .dropna(subset=[metr])
            )

            # considera solo mesi con valore strettamente positivo
            recent_months = recent_months[recent_months[metr] > 0]["mese"].unique().tolist()

            # Ordine naturale dei mesi
            mesi_ordine = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
            mesi_disponibili = [m for m in mesi_ordine if m in recent_months]

            if not mesi_disponibili:
                st.warning(f"Impossibile calcolare la variazione: non ci sono mesi con dati (>0) per l'anno {anno_recent}.")
            else:
                # Filtra entrambi gli anni solo sui mesi disponibili (con dati) del recent year
                mask_prev = (stl_filtrata["anno"] == anno_prev) & (stl_filtrata["mese"].isin(mesi_disponibili))
                mask_recent = (stl_filtrata["anno"] == anno_recent) & (stl_filtrata["mese"].isin(mesi_disponibili))

                prev_val = stl_filtrata.loc[mask_prev, metr].sum()
                recent_val = stl_filtrata.loc[mask_recent, metr].sum()

                # calcolo variazione protetto da divisione per zero
                if prev_val and prev_val != 0:
                    var_pct = ((recent_val - prev_val) / prev_val) * 100
                else:
                    var_pct = float("nan")

                # colore
                color = "green" if (not pd.isna(var_pct) and var_pct > 0) else ("red" if (not pd.isna(var_pct) and var_pct < 0) else "grey")

                # mostra quali mesi sono stati usati per il confronto
                mesi_str = ", ".join(mesi_disponibili)
                st.markdown(
                    f"<div style='font-size:13px;color:gray;'>Confronto effettuato sui mesi con dati in {anno_recent}: <i>{mesi_str}</i></div>",
                    unsafe_allow_html=True
                )

                display_var = f"{var_pct:+.2f}%" if not pd.isna(var_pct) else "N/A"
                st.markdown(
                    f"<div style='font-size:20px;'><b>Variazione complessiva {sel_metrica}</b> "
                    f"{anno_recent} vs {anno_prev}: "
                    f"<span style='color:{color};'>{display_var}</span></div>",
                    unsafe_allow_html=True
                )

        # ======================
        # 📈 GRAFICO STL
        # ======================
        st.subheader(f"📈 Andamento mensile {sel_metrica}")
        fig = px.line(stl_filtrata, x="mese", y=sel_metrica.lower(), color="anno", markers=True)
        fig.update_layout(xaxis=dict(categoryorder="array", categoryarray=mesi_validi))
        st.plotly_chart(fig, use_container_width=True)

        # ======================
        # 📊 TABELLA CONFRONTO TRA ANNI
        # ======================
        st.subheader(f"📊 Confronto tra anni e mesi – Differenze e variazioni {sel_metrica}")

        tabella_stl = (
            stl_filtrata.groupby(["anno", "mese"])[sel_metrica.lower()]
            .sum()
            .reset_index()
            .pivot_table(index="mese", columns="anno", values=sel_metrica.lower(), fill_value=0)
        )

        tabella_stl = tabella_stl.reindex(mesi_validi)

        # Aggiungi riga totale
        totale = pd.DataFrame(tabella_stl.sum()).T
        totale.index = ["Totale"]
        tabella_stl = pd.concat([tabella_stl, totale])

        # Se due anni selezionati → differenze e % variazioni
        if len(anni_sel_stl) == 2:
            anno_prev, anno_recent = sorted(anni_sel_stl)
            tabella_stl["Differenza"] = tabella_stl[anno_recent] - tabella_stl[anno_prev]
            tabella_stl["Variazione %"] = (tabella_stl["Differenza"] / tabella_stl[anno_prev].replace(0, pd.NA)) * 100

            def color_var(val):
                if pd.isna(val):
                    return "color: grey;"
                elif val > 0:
                    return "color: green; font-weight: bold;"
                elif val < 0:
                    return "color: red; font-weight: bold;"
                else:
                    return "color: grey;"

            fmt = {col: "{:,.0f}".format for col in tabella_stl.columns if col != "Variazione %"}
            fmt["Variazione %"] = "{:.2f}%"

            styled = (
                tabella_stl.style.format(fmt, thousands=".")
                .applymap(color_var, subset=["Variazione %"])
            )

            st.markdown(
                f"**Confronto tra {anno_recent} e {anno_prev}:** differenze e variazioni calcolate come *{anno_recent} − {anno_prev}*."
            )
            st.dataframe(styled, use_container_width=True)
        else:
            fmt = {col: "{:,.0f}".format for col in tabella_stl.columns if tabella_stl[col].dtype != "O"}
            st.dataframe(tabella_stl.style.format(fmt, thousands="."), use_container_width=True)

# ======================
# 🧾 FOOTER
# ======================
st.caption("© 2025 Dashboard Fondazione D.M.O. Dolomiti Bellunesi – Uso interno")
