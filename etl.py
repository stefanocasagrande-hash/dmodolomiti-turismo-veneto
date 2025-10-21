import os
import pandas as pd

# =========================
# 1️⃣ CARICAMENTO DATI COMUNALI
# =========================
def load_data(data_folder="dmodolomiti-turismo-veneto/dati-mensili-per-comune"):
    """
    Carica tutti i file con dati mensili per Comune (es. 2023, 2024, ecc.)
    e li combina in un unico DataFrame.
    """
    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    if not os.path.exists(data_folder):
        print(f"⚠️ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

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

            # Normalizza colonne
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
# 2️⃣ CARICAMENTO DATI PROVINCIALI
# =========================
def load_provincia_belluno(data_folder="dmodolomiti-turismo-veneto/dati-provincia-annuali"):
    frames = []
    ordine_mesi = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ]

    if not os.path.exists(data_folder):
        print(f"⚠️ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if not file.endswith(".txt"):
            continue

        path = os.path.join(data_folder, file)
        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        year = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(year) if year else None

        if "mese" not in df.columns:
            continue

        df["mese"] = df["mese"].str.capitalize()
        df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)

        df.rename(columns={
            "totale_arrivi": "arrivi",
            "totale_presenze": "presenze"
        }, inplace=True, errors="ignore")

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    return data


# =========================
# 3️⃣ CARICAMENTO DATI STL (Dolomiti e Belluno)
# =========================
def load_stl_data(base_folder="dmodolomiti-turismo-veneto/stl-presenze-arrivi"):
    """
    Carica tutti i file STL Dolomiti e STL Belluno e restituisce due DataFrame.
    """
    def _load_stl_subfolder(subfolder):
        frames = []
        ordine_mesi = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        path_dir = os.path.join(base_folder, subfolder)
        if not os.path.exists(path_dir):
            print(f"⚠️ Cartella non trovata: {path_dir}")
            return pd.DataFrame()

        for file in os.listdir(path_dir):
            if not file.endswith(".txt"):
                continue
            path = os.path.join(path_dir, file)
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")

            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            year = "".join([c for c in file if c.isdigit()])
            df["anno"] = int(year) if year else None
            if "mese" in df.columns:
                df["mese"] = df["mese"].str.capitalize()
                df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    stl_dolomiti = _load_stl_subfolder("stl-dolomiti")
    stl_belluno = _load_stl_subfolder("stl-belluno")
    return stl_dolomiti, stl_belluno
