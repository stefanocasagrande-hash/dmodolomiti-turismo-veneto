import pandas as pd
import os
import glob

def load_data(data_dir="dati-paesi-di-provenienza", prefix="presenze-dolomiti-estero"):
    """
    Carica e combina tutti i file di presenze turistiche per anno.
    I file devono avere nomi come: presenze-dolomiti-estero-2023.txt, presenze-dolomiti-estero-2024.txt, ecc.
    """

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"❌ La cartella '{data_dir}' non esiste.")

    # Cerca tutti i file con prefisso corretto
    pattern = os.path.join(data_dir, f"{prefix}-*.txt")
    all_files = sorted(glob.glob(pattern))

    if not all_files:
        raise FileNotFoundError(
            f"❌ Nessun file trovato in '{data_dir}' con prefisso '{prefix}-'. "
            "Assicurati che i file siano presenti e abbiano nomi come 'presenze-dolomiti-estero-2024.txt'."
        )

    df_list = []

    for file in all_files:
        try:
            # Estrae l’anno dal nome del file
            year = file.split("-")[-1].split(".")[0]

            # Legge il file (header alla seconda riga, separatore ';')
            df = pd.read_csv(file, sep=";", header=1, engine="python")

            # Rinomina la prima colonna in “Mese”
            df.rename(columns={df.columns[0]: "Mese"}, inplace=True)
            df["Anno"] = int(year)
            df_list.append(df)

        except Exception as e:
            print(f"⚠️ Errore durante la lettura di {file}: {e}")

    if not df_list:
        raise ValueError("❌ Nessun file valido è stato caricato.")

    # Combina tutti i DataFrame
    df = pd.concat(df_list, ignore_index=True)

    # Trasforma i dati in formato lungo
    df_long = df.melt(
        id_vars=["Anno", "Mese"],
        var_name="Paese",
        value_name="Presenze"
    )

    # Pulisce i dati
    df_long = df_long.dropna(subset=["Presenze"])
    df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce").fillna(0).astype(int)

    # Ordina i mesi in ordine cronologico
    mesi_ordine = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]
    df_long["Mese"] = pd.Categorical(df_long["Mese"], categories=mesi_ordine, ordered=True)

    return df_long
