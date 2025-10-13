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
