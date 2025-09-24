import pandas as pd
import os

def load_data(data_folder="dati-mensili-per-comune"):
    all_dfs = []
    for file in os.listdir(data_folder):
        if file.endswith(".txt") or file.endswith(".csv"):
            path = os.path.join(data_folder, file)
            df = pd.read_csv(path, sep=";")
            
            # Pulizia colonne
            df = df.rename(columns=lambda x: x.strip())
            
            # Trasforma da wide a long (un mese per riga)
            df_long = df.melt(
                id_vars=["anno", "provenienza", "Comuni"],
                value_vars=[col for col in df.columns if "Presenze" in col],
                var_name="mese",
                value_name="presenze"
            )
            
            # Normalizza i nomi dei mesi
            df_long["mese"] = df_long["mese"].str.replace(" Presenze", "", regex=False)
            
            all_dfs.append(df_long)
    
    # Unisci tutti gli anni
    data = pd.concat(all_dfs, ignore_index=True)
    
    # Estrai solo il nome del Comune (senza codice numerico davanti)
    data["Comune"] = data["Comuni"].str.split(" - ").str[1]
    
    return data