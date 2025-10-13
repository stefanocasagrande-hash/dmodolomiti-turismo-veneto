import os
import pandas as pd

# =========================
# 1️⃣ CARICAMENTO DATI COMUNALI
# =========================
def load_data(data_folder="dati-mensili-per-comune"):
    """
    Carica tutti i file con dati mensili per Comune (es. 2023, 2024, ecc.)
    e li combina in un unico DataFrame.
    """
    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    for file in os.listdir(data_folder):
        if file.endswith(".txt"):
            path = os.path.join(data_folder, file)
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")

            # Pulizia colonne
            df.columns = [c.strip().lower() for c in df.columns]

            # Determina anno dal nome file
            year = "".join([c for c in file if c.isdigit()])
            df["anno"] = int(year) if year else None

            # Normalizzazione colonne base
            if "comune" not in df.columns:
                df.rename(columns={"denominazione_comune": "comune"}, inplace=True)
            if "presenze" not in df.columns:
                continue

            # Normalizza mese
            if "mese" in df.columns:
                df["mese"] = df["mese"].str.strip().str[:3].str.capitalize()
                df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)
            else:
                continue

            df = df.dropna(subset=["comune", "presenze"])
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "mese", "comune"])
    return data


# =========================
# 2️⃣ CARICAMENTO DATI PROVINCIALI (BELLUNO)
# =========================
def load_provincia_belluno(data_folder="dati-mensili-per-comune/dati-provincia-annuali"):
    """
    Carica i file degli arrivi e presenze totali per la provincia di Belluno
    presenti nella cartella specificata (uno per anno).
    Adatta la struttura del file ufficiale (Arrivi/Presenze italiani e stranieri).
    """
    import os
    frames = []
    ordine_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                   "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

    if not os.path.exists(data_folder):
        print(f"⚠️ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if file.endswith(".txt") and "belluno" in file.lower():
            path = os.path.join(data_folder, file)
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")

            # Rinomina colonne
            df.columns = [c.strip().lower() for c in df.columns]
            rename_map = {
                "mese": "mese",
                "totale arrivi": "arrivi",
                "totale presenze": "presenze"
            }
            df.rename(columns=rename_map, inplace=True)

            # Elimina righe di totale
            df = df[~df["mese"].str.upper().str.contains("TOTALE")]

            # Estrai anno dal file o dalla colonna 'anno'
            if "anno" in df.columns:
                df["anno"] = df["anno"].astype(str).str.extract(r"(\d{4})").astype(int)
            else:
                year = "".join([c for c in file if c.isdigit()])
                df["anno"] = int(year) if year else None

            # Normalizza mese
            df["mese"] = df["mese"].str.strip().str.capitalize()
            df["mese"] = df["mese"].replace({
                "Gennaio": "Gen", "Febbraio": "Feb", "Marzo": "Mar", "Aprile": "Apr",
                "Maggio": "Mag", "Giugno": "Giu", "Luglio": "Lug", "Agosto": "Ago",
                "Settembre": "Set", "Ottobre": "Ott", "Novembre": "Nov", "Dicembre": "Dic"
            })
            df["mese"] = pd.Categorical(df["mese"],
                                        categories=["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                                                    "Lug", "Ago", "Set", "Ott", "Nov", "Dic"],
                                        ordered=True)

            # Mantieni solo le colonne utili
            df = df[["mese", "anno", "arrivi", "presenze"]]
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    df_belluno = pd.concat(frames, ignore_index=True)
    df_belluno = df_belluno.sort_values(["anno", "mese"])
    return df_belluno

