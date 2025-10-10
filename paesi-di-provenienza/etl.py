import pandas as pd
import os
import glob

def load_data(data_dir="dati-paesi-di-provenienza", prefix="presenze-dolomiti-estero"):
    """
    Carica i file di presenze turistiche in formato:
    presenze-dolomiti-estero-2023.txt, presenze-dolomiti-estero-2024.txt, ecc.
    Restituisce un DataFrame in formato lungo: [Anno, Mese, Paese, Presenze]
    """

    # --- Controllo cartella ---
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"La cartella '{data_dir}' non esiste.")

    # --- Cerca tutti i file corrispondenti ---
    pattern = os.path.join(data_dir, f"{prefix}-*.txt")
    all_files = sorted(glob.glob(pattern))

    if not all_files:
        raise FileNotFoundError(f"Nessun file trovato in '{data_dir}' con prefisso '{prefix}-'.")

    df_list = []

    # --- Lettura dei file ---
    for file in all_files:
        try:
            # Estrae l’anno dal nome file
            year = int(os.path.basename(file).split("-")[-1].split(".")[0])

            # Legge il file: separatore ";" e header alla seconda riga (header=1)
            df = pd.read_csv(file, sep=";", header=1, engine="python")

            # Rinomina la prima colonna in "Mese"
            # Trova automaticamente la colonna che contiene la parola "MESE"
            col_mese = next((c for c in df.columns if "MESE" in c.upper()), df.columns[0])
            df.rename(columns={col_mese: "Mese"}, inplace=True)
            df["Anno"] = year

            df_list.append(df)
        except Exception as e:
            print(f"⚠️ Errore nel file {file}: {e}")

    if not df_list:
        raise ValueError("Nessun file valido caricato — controlla il formato dei file.")

    # --- Combina tutti i DataFrame ---
    df = pd.concat(df_list, ignore_index=True)

    # --- Trasforma da formato largo a lungo ---
    df_long = df.melt(id_vars=["Mese", "Anno"], var_name="Paese", value_name="Presenze")

    # --- Pulizia e conversione ---
    df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce").fillna(0).astype(int)

    # 🔧 Pulizia nomi Paesi
    df_long["Paese"] = (
        df_long["Paese"]
        .astype(str)
        .str.replace(" Paese", "", regex=False)
        .str.strip()
    )

    # 🔧 Pulizia nomi Mesi (rimuove numeri iniziali tipo "01Gennaio")
    df_long["Mese"] = (
        df_long["Mese"]
        .astype(str)
        .str.replace(r"^\d+", "", regex=True)
        .str.strip()
    )

    # --- Ordina i mesi in ordine cronologico ---
    mesi_ordine = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]
    df_long["Mese"] = pd.Categorical(df_long["Mese"], categories=mesi_ordine, ordered=True)

    # --- Rimuove righe vuote o non valide ---
    df_long = df_long[df_long["Mese"].notna() & df_long["Paese"].notna()]

    return df_long
