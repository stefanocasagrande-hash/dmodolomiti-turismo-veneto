import pandas as pd
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "dati-paesi-di-provenienza")

def load_data():
    all_data = []

    for file_name in os.listdir(DATA_DIR):
        if file_name.endswith(".txt"):
            file_path = os.path.join(DATA_DIR, file_name)

            # estraggo l'anno dal nome file (cerca 4 cifre)
            match = re.search(r"(\d{4})", file_name)
            anno = int(match.group(1)) if match else None

            # leggo il file: la riga 2 contiene i Paesi
            df = pd.read_csv(file_path, sep=";", header=1)

            # rinomino la prima colonna come "Mese"
            df = df.rename(columns={df.columns[0]: "Mese"})

            # trasformo in formato lungo
            df_long = df.melt(
                id_vars=["Mese"],
                var_name="Paese",
                value_name="Presenze"
            )

            # aggiungo colonna anno
            df_long["Anno"] = anno

            all_data.append(df_long)

    # unisco tutti i file
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame(columns=["Mese", "Paese", "Presenze", "Anno"])


if __name__ == "__main__":
    print(load_data().head(20))