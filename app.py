import streamlit as st
import os
import glob
import pandas as pd
from etl import load_data, load_provincia_belluno

st.set_page_config(page_title="Debug Dati Turistici Veneto", layout="wide")

st.title("🔍 Debug caricamento dati turistici Veneto")

st.info("""
Questa è una **versione temporanea** dell'app usata per verificare il caricamento dei file.
Dopo che avremo confermato che i percorsi e i dati sono corretti,
torneremo alla dashboard completa.
""")

# Mostra working directory e file trovati
cwd = os.getcwd()
st.markdown(f"**📂 Directory di lavoro:** `{cwd}`")

# Cerca file ricorsivamente
turismo_files = glob.glob(os.path.join(cwd, "**", "turismo-per-mese-comune*.txt"), recursive=True)
provincia_files = glob.glob(os.path.join(cwd, "**", "presenze-arrivi-provincia-belluno*.txt"), recursive=True)

col1, col2 = st.columns(2)
with col1:
    st.subheader("📁 File comunali trovati:")
    if turismo_files:
        for f in turismo_files:
            st.write("✅", f)
    else:
        st.error("❌ Nessun file 'turismo-per-mese-comune-*.txt' trovato.")

with col2:
    st.subheader("📁 File provinciali trovati:")
    if provincia_files:
        for f in provincia_files:
            st.write("✅", f)
    else:
        st.error("❌ Nessun file 'presenze-arrivi-provincia-belluno-*.txt' trovato.")

st.divider()

# Test caricamento dei dati comunali
st.subheader("📊 Test caricamento dati comunali")
try:
    data = load_data()
    if not data.empty:
        st.success(f"✅ Dati comunali caricati: {len(data):,} righe, {data['anno'].nunique()} anni, {data['comune'].nunique()} comuni.")
        st.dataframe(data.head(10))
    else:
        st.error("❌ Nessun dato comunale caricato.")
except Exception as e:
    st.exception(e)

st.divider()

# Test caricamento dati provinciali
st.subheader("🏔️ Test caricamento dati provincia di Belluno")
try:
    provincia = load_provincia_belluno()
    if not provincia.empty:
        st.success(f"✅ Dati provinciali caricati: {len(provincia):,} righe, {provincia['anno'].nunique()} anni.")
        st.dataframe(provincia.head(10))
    else:
        st.error("❌ Nessun dato provinciale caricato.")
except Exception as e:
    st.exception(e)

st.divider()
st.caption("🧠 Fine diagnostica. Se i file e i dati appaiono corretti, possiamo tornare alla versione completa della dashboard.")
