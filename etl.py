import pandas as pd
import os

def load_data(data_folder="dati-mensili-per-comune"):
    all_dfs = []

    if not os.path.exists(data_folder):
        print(f"⚠️ Cartella non trovata: {data_folder}")
        return pd.DataFrame(columns=["anno", "provenienza", "Comuni", "mese", "presenze", "Comune"])

    for file in os.listdir(data_folder):
        if file.endswith(".txt") or file.endswith(".csv"):
            path = os.path.join(data_folder, file)
            size = os.path.getsize(path)
            print(f"📂 Tentativo di lettura file: {file} (size={size} bytes)")

            if size == 0:
                print(f"⚠️ File vuoto ignorato: {file}")
                continue

            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except (pd.errors.EmptyDataError, UnicodeDecodeError):
                try:
                    df = pd.read_csv(path, sep=";", encoding="latin-1")
                except Exception as e:
                    print(f"❌ Errore nel leggere {file}: {e}")
                    continue

            if df.empty:
                print(f"⚠️ Nessun dato in {file}, file ignorato")
                continue

            # Pulizia colonne
            df = df.rename(columns=lambda x: x.strip())

            # Trasforma da wide a long
            if "Comuni" in df.columns and "anno" in df.columns:
                df_long = df.melt(
                    id_vars=["anno", "provenienza", "Comuni"],
                    value_vars=[col for col in df.columns if "Presenze" in col],
                    var_name="mese",
                    value_name="presenze"
                )

                df_long["mese"] = df_long["mese"].str.replace(" Presenze", "", regex=False)
                df_long["Comune"] = df_long["Comuni"].str.split(" - ").str[1]

                all_dfs.append(df_long)
            else:
                print(f"⚠️ File {file} ignorato: colonne attese non trovate")

    if all_dfs:
        print(f"✅ Caricati {len(all_dfs)} file validi")
        return pd.concat(all_dfs, ignore_index=True)
    else:
        print("⚠️ Nessun file valido trovato")
        return pd.DataFrame(columns=["anno", "provenienza", "Comuni", "mese", "presenze", "Comune"])
