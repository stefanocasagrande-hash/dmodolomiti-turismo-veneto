import pandas as pd
import os

def load_data(data_folder="dati-mensili-per-comune"):
    all_dfs = []
    if not os.path.exists(data_folder):
        return pd.DataFrame(columns=["anno", "provenienza", "Comuni", "mese", "presenze", "Comune"])

    for file in os.listdir(data_folder):
        if file.endswith(".txt") or file.endswith(".csv"):
            path = os.path.join(data_folder, file)
            if os.path.getsize(path) == 0:
                continue

            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin-1")
            except pd.errors.EmptyDataError:
                continue

            df = df.rename(columns=lambda x: x.strip())

            df_long = df.melt(
                id_vars=["anno", "provenienza", "Comuni"],
                value_vars=[col for col in df.columns if "Presenze" in col],
                var_name="mese",
                value_name="presenze"
            )

            df_long["mese"] = df_long["mese"].str.replace(" Presenze", "", regex=False)
            df_long["Comune"] = df_long["Comuni"].str.split(" - ").str[1]

            all_dfs.append(df_long)

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame(columns=["anno", "provenienza", "Comuni", "mese", "presenze", "Comune"])
