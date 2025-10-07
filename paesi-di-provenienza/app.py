import streamlit as st
import pandas as pd
import glob
import os
import altair as alt

# === Configurazione pagina ===
st.set_page_config(page_title="Presenze turistiche per Paese", layout="wide")

st.title("📊 Dashboard Presenze Turistiche per Paese di Provenienza")

# === Caricamento dinamico file ===
data_folder = "dati-paesi-di-provenienza"
files = glob.glob(os.path.join(data_folder, "presenze-dolomiti-estero-*.txt"))

df_all = []
for f in files:
    basename = os.path.basename(f)
    anno = os.path.splitext(basename)[0].split("-")[-1]  # estrae anno dal nome file
    
    df = pd.read_csv(f, sep=";", header=1, engine="python")
    df.rename(columns={df.columns[0]: "Mese"}, inplace=True)
    
    df_long = df.melt(id_vars=["Mese"], var_name="Paese", value_name="Presenze")
    df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce").fillna(0)
    df_long["Anno"] = anno
    df_all.append(df_long)

if df_all:
    df_all = pd.concat(df_all, ignore_index=True)
else:
    st.error("❌ Nessun file trovato nella cartella dati-paesi-di-provenienza")
    st.stop()

# === Filtri Sidebar ===
st.sidebar.header("🎛️ Filtri")

anni_unici = sorted(df_all["Anno"].unique())
paesi_unici = sorted(df_all["Paese"].unique())
mesi_unici = sorted(df_all["Mese"].unique())

anni_sel = st.sidebar.multiselect(
    "📅 Seleziona Anno/i",
    anni_unici,
    default=anni_unici,
)

paesi_sel = st.sidebar.multiselect(
    "🌍 Seleziona Paese/i",
    paesi_unici,
    default=["Germania Paese", "Austria Paese", "Francia Paese"],
)

mesi_sel = st.sidebar.multiselect(
    "📆 Seleziona Mese/i",
    mesi_unici,
    default=mesi_unici,
)

# === Applico i filtri ===
df_filt = df_all[df_all["Anno"].isin(anni_sel)]
if paesi_sel:
    df_filt = df_filt[df_filt["Paese"].isin(paesi_sel)]
if mesi_sel:
    df_filt = df_filt[df_filt["Mese"].isin(mesi_sel)]

# === Ordine mesi coerente ===
ordine_mesi = [
    "01Gennaio", "02Febbraio", "03Marzo", "04Aprile",
    "05Maggio", "06Giugno", "07Luglio", "08Agosto",
    "09Settembre", "10Ottobre", "11Novembre", "12Dicembre"
]

df_filt["Mese"] = pd.Categorical(df_filt["Mese"], categories=ordine_mesi, ordered=True)
df_filt = df_filt.sort_values(["Anno", "Paese", "Mese"])

# === Colonna combinata Paese + Anno ===
df_filt["Serie"] = df_filt["Paese"] + " (" + df_filt["Anno"].astype(str) + ")"

# === Grafico con legenda unica ===
chart = (
    alt.Chart(df_filt)
    .mark_line(point=True)
    .encode(
        x=alt.X("Mese:N", sort=ordine_mesi, title="Mese"),
        y=alt.Y("Presenze:Q", title="Presenze"),
        color=alt.Color("Serie:N", title="Paese / Anno"),
        tooltip=["Anno", "Paese", "Mese", "Presenze"]
    )
    .properties(width=900, height=500, title="Andamento presenze per Paese e Anno")
)

st.altair_chart(chart, use_container_width=True)

# === Tabella di confronto anni ===
if len(anni_sel) >= 2:
    pivot = df_filt.pivot_table(
        index=["Mese", "Paese"],
        columns="Anno",
        values="Presenze",
        aggfunc="sum"
    ).reset_index()

    anni_sorted = sorted(anni_sel)
    anno1, anno2 = anni_sorted[0], anni_sorted[-1]
    if anno1 in pivot.columns and anno2 in pivot.columns:
        pivot["Diff assoluta"] = pivot[anno2] - pivot[anno1]
        pivot["Diff %"] = ((pivot[anno2] - pivot[anno1]) / pivot[anno1].replace(0, pd.NA)) * 100

    st.subheader(f"📋 Confronto {anno1} vs {anno2}")
    st.dataframe(pivot.style.format({"Diff %": "{:.2f}%"}))
else:
    st.subheader("📋 Dati filtrati")
    st.dataframe(df_filt)