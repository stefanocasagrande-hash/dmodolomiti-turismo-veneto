import pandas as pd
import os
import glob

def load_data(data_dir="dati-paesi-di-provenienza", prefix="turismo-per-mese-comune", suffix="-presenze.txt"):
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"La cartella '{data_dir}' non esiste.")

    all_files = glob.glob(os.path.join(data_dir, f"{prefix}-*-{suffix}"))

    if not all_files:
        raise FileNotFoundError(f"Nessun file trovato in '{data_dir}' con prefisso '{prefix}'.")

    df_list = []
    for file in all_files:
        try:
            # Estrae l’anno dal nome del file
            year = [int(s) for s in os.path.basename(file).split("-") if s.isdigit()][0]
            df = pd.read_csv(file, sep=";", engine="python")
            df["Anno"] = year
            df_list.append(df)
        except Exception as e:
            print(f"Errore nel file {file}: {e}")

    df = pd.concat(df_list, ignore_index=True)

    # Uniforma nomi colonne
    df.columns = [c.strip().capitalize() for c in df.columns]

    # Conversione dati long se necessario
    if "Paese" not in df.columns and "Nazione" in df.columns:
        df.rename(columns={"Nazione": "Paese"}, inplace=True)

    df_long = df.melt(
        id_vars=["Anno", "Paese"],
        var_name="Mese",
        value_name="Presenze"
    )

    # Rimuove valori nulli o negativi
    df_long = df_long.dropna(subset=["Presenze"])
    df_long = df_long[df_long["Presenze"] >= 0]

    return df_long
