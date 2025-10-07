import os
import pandas as pd

def load_data(data_dir="dati-paesi-di-provenienza"):
    """
    Carica e unisce tutti i file di presenze turistiche estero per anno.
    Restituisce un DataFrame in formato lungo con colonne:
    ['Anno', 'Mese', 'Paese', 'Presenze']
    """

    all_data = []

    for file in os.listdir(data_dir):
        if file.startswith("presenze-dolomiti-estero") and file.endswith(".txt"):
            try:
                anno = int(file.split("-")[-1].split(".")[0])
                path = os.path.join(data_dir, file)

                # Leggi il file (header sulla riga 2 → header=1)
                df = pd.read_csv(path, sep=";", header=1, engine="python")

                # Rinomina la prima colonna
                df = df.rename(columns={df.columns[0]: "Mese"})
                df["Anno"] = anno
                all_data.append(df)
            except Exception as e:
                print(f"Errore nel caricamento di {file}: {e}")

    if not all_data:
        raise FileNotFoundError("Nessun file trovato nella cartella dati-paesi-di-provenienza")

    # Unisci tutti i file caricati
    df = pd.concat(all_data, ignore_index=True)

    # Trasforma i dati in formato lungo
    df_long = df.melt(id_vars=["Mese", "Anno"], var_name="Paese", value_name="Presenze")

    # Pulisci e converti i valori
    df_long["Presenze"] = pd.to_numeric(df_long["Presenze"], errors="coerce")
    df_long = df_long.dropna(subset=["Presenze"])

    # Rimuovi numeri iniziali dai mesi (es. '01Gennaio' → 'Gennaio')
    df_long["Mese"] = df_long["Mese"].astype(str).str.replace(r"^\d+", "", regex=True)

    # Ordina i mesi
    mesi_ordine = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]
    df_long["Mese"] = pd.Categorical(df_long["Mese"], categories=mesi_ordine, ordered=True)

    return df_long
