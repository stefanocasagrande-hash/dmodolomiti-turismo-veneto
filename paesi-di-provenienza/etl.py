import pandas as pd
import os
import glob

def load_data(data_dir="dati-paesi-di-provenienza", prefix="presenze-dolomiti-estero"):
    """
    Carica i file con nomi tipo 'presenze-dolomiti-estero-2023.txt'
    e li combina in un unico DataFrame lungo.
    """

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"La cartella '{data_dir}' non esiste.")

    pattern = os.path.join(data_dir, f"{prefix}-*.txt")
    all_files = sorted(glob.glob(pattern))

    if not all_files:
        raise FileNotFoundError(f"Nessun file trovato in '{data_dir}' con prefisso '{prefix}-'.")

    df_list = []

    for file in all_files:
        try:
            year = int(os.path.basename(file).split("-")[-1].split(".")[0])
            # ✅ Header alla seconda riga, separatore ';'
            df = pd.read_csv(file, sep=";", header=1, engine="python")
            # Rinomina la prima colonna
            df.rename(columns={df.columns[0]: "Mese"}, inplace=True)
            df["Anno"] = year
            df_list.append(df)
        except Exception as e:
            print(f"Errore nel file {file}: {e}")

    if not df_list:
        raise ValueError("Nessun file valido caricato — controlla il formato dei file.")

    # Unisci tutti i DataFrame
    df = pd.concat(df_list, ignore_index=True)

    # Trasforma i dati in formato lungo
df_long = df.melt(id_vars=["Mese", "Anno"], var_name="Paese", value_name="Presenze")

# Pulisci e converte
df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce").fillna(0).astype(int)

# 🔧 Pulizia nomi Paesi e mesi
df_long["Paese"] = df_long["Paese"].astype(str).str.replace(" Paese", "", regex=False).str.strip()
df_long["Mese"] = (
    df_long["Mese"]
    .astype(str)
    .str.replace(r"^\d+", "", regex=True)
    .str.strip()
)

# Ordina i mesi
mesi_ordine = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
]
df_long["Mese"] = pd.Categorical(df_long["Mese"], categories=mesi_ordine, ordered=True)

    return df_long
