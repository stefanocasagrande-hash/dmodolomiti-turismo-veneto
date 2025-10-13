import os
import pandas as pd

# =========================
# 1️⃣ CARICAMENTO DATI COMUNALI
# =========================
def load_data(data_folder="dati-mensili-per-comune"):
    """
    Carica tutti i file con dati mensili per Comune (es. 2023, 2024, ecc.)
    e li combina in un unico DataFrame.
    Ignora automaticamente file vuoti o non validi.
    """
    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    if not os.path.exists(data_folder):
        print(f"⚠️ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if not file.endswith(".txt"):
            continue

        path = os.path.join(data_folder, file)
        try:
            if os.path.getsize(path) == 0:
                print(f"⚠️ File vuoto saltato: {file}")
                continue

            df = pd.read_csv(path, sep=";", encoding="utf-8")
            if df.empty:
                print(f"⚠️ File senza dati: {file}")
                continue

        except (pd.errors.EmptyDataError, UnicodeDecodeError, pd.errors.ParserError):
            print(f"⚠️ File non leggibile: {file}")
            continue

        # Pulizia colonne
        df.columns = [c.strip().lower() for c in df.columns]
        year = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(year) if year else None

        if "comune" not in df.columns:
            df.rename(columns={"denominazione_comune": "comune"}, inplace=True)

        if "presenze" not in df.columns or "mese" not in df.columns:
            print(f"⚠️ Colonne mancanti in {file}, saltato.")
            continue

        df["mese"] = df["mese"].str.strip().str[:3].str.capitalize()
        df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)
        df = df.dropna(subset=["comune", "presenze"])

        frames.append(df)

    if not frames:
        print("⚠️ Nessun file valido trovato nella cartella.")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "mese", "comune"])
    return data


# =========================
# 2️⃣ CARICAMENTO DATI PROVINCIALI (BELLUNO)
# =========================
def load_provincia_belluno(data_folder="dati-provincia-annuali"):
    """
    Carica i file degli arrivi e presenze totali per la provincia di Belluno.
    Gestisce la struttura dei file con colonne 'Totale arrivi' e 'Totale presenze'.
    """
    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

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

            df.columns = [c.strip().lower() for c in df.columns]
            rename_map = {
                "mese": "mese",
                "totale arrivi": "arrivi",
                "totale presenze": "presenze"
            }
            df.rename(columns=rename_map, inplace=True)

            if "mese" not in df.columns or "arrivi" not in df.columns or "presenze" not in df.columns:
                print(f"⚠️ Colonne non trovate in {file}, saltato.")
                continue

            # Elimina riga "TOTALE"
            df = df[~df["mese"].str.upper().str.contains("TOTALE", na=False)]

            # Estrai anno
            if "anno" in df.columns:
                df["anno"] = df["anno"].astype(str).str.extract(r"(\d{4})").astype(int)
            else:
                year = "".join([c for c in file if c.isdigit()])
                df["anno"] = int(year) if year else None

            # Normalizza mesi (da "Gennaio" → "Gen")
            df["mese"] = df["mese"].str.strip().str.capitalize()
            df["mese"] = df["mese"].replace({
                "Gennaio": "Gen", "Febbraio": "Feb", "Marzo": "Mar", "Aprile": "Apr",
                "Maggio": "Mag", "Giugno": "Giu", "Luglio": "Lug", "Agosto": "Ago",
                "Settembre": "Set", "Ottobre": "Ott", "Novembre": "Nov", "Dicembre": "Dic"
            })
            df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)
            df = df[["mese", "anno", "arrivi", "presenze"]].sort_values(["anno", "mese"])

            frames.append(df)

    if not frames:
        print("⚠️ Nessun file provinciale valido trovato.")
        return pd.DataFrame()

    df_belluno = pd.concat(frames, ignore_index=True)
    return df_belluno
