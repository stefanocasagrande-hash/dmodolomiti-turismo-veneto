import os
import pandas as pd

# =========================
# 📁 Utility per i percorsi
# =========================
def _resolve_path(relative_path: str) -> str:
    """
    Restituisce il percorso assoluto, anche se l'app è eseguita da directory diverse.
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, relative_path)

    if not os.path.exists(full_path):
        # Tentativo aggiuntivo: includi la cartella madre 'stefanocasagrande-hash'
        alt_path = os.path.join(base_path, "stefanocasagrande-hash", relative_path)
        if os.path.exists(alt_path):
            return alt_path
        print(f"⚠️ Percorso non trovato: {full_path}")
        return relative_path
    return full_path


# =========================
# 1️⃣ CARICAMENTO DATI COMUNALI
# =========================
def load_dati_comunali(data_folder="dmodolomiti-turismo-veneto/dati-mensili-per-comune"):
    data_folder = _resolve_path(data_folder)
    frames = []

    mesi_map = {
        "Gen": "Gennaio", "Feb": "Febbraio", "Mar": "Marzo", "Apr": "Aprile",
        "Mag": "Maggio", "Giu": "Giugno", "Lug": "Luglio", "Ago": "Agosto",
        "Set": "Settembre", "Ott": "Ottobre", "Nov": "Novembre", "Dic": "Dicembre"
    }

    if not os.path.exists(data_folder):
        print(f"❌ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if not file.lower().endswith(".txt"):
            continue
        path = os.path.join(data_folder, file)

        if os.path.getsize(path) == 0:
            print(f"⚠️ File vuoto saltato: {file}")
            continue

        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")
        except Exception as e:
            print(f"⚠️ Errore nella lettura di {file}: {e}")
            continue

        if "Comuni" not in df.columns:
            print(f"⚠️ File senza colonna 'Comuni': {file}")
            continue

        # Estrai anno dal nome file
        year = "".join([c for c in file if c.isdigit()])
        anno = int(year) if year else None

        # Trasforma le colonne mensili in formato lungo
        mesi_cols = [c for c in df.columns if "Presenze" in c and any(m in c for m in mesi_map.keys())]
        df_long = df.melt(
            id_vars=["Comuni"],
            value_vars=mesi_cols,
            var_name="mese",
            value_name="presenze"
        )

        df_long["mese"] = df_long["mese"].str.extract(r"^(\w{3})")[0]
        df_long["mese"] = pd.Categorical(df_long["mese"], categories=list(mesi_map.keys()), ordered=True)

        df_long["anno"] = anno
        df_long["comune"] = df_long["Comuni"].str.strip()
        df_long.drop(columns=["Comuni"], inplace=True)
        df_long["presenze"] = pd.to_numeric(df_long["presenze"], errors="coerce").fillna(0).astype(int)

        frames.append(df_long)

    if not frames:
        print("⚠️ Nessun file valido trovato.")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "comune", "mese"])
    return data


# =========================
# 2️⃣ CARICAMENTO DATI PROVINCIALI
# =========================
def load_provincia_belluno(data_folder="dmodolomiti-turismo-veneto/dati-provincia-annuali"):
    data_folder = _resolve_path(data_folder)
    frames = []

    if not os.path.exists(data_folder):
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if not file.endswith(".txt"):
            continue
        path = os.path.join(data_folder, file)

        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")

        df.columns = [c.strip().lower() for c in df.columns]
        if not {"mese", "totale arrivi", "totale presenze"}.issubset(df.columns):
            continue

        df["arrivi"] = df["totale arrivi"]
        df["presenze"] = df["totale presenze"]
        frames.append(df[["anno", "mese", "arrivi", "presenze"]])

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# =========================
# 3️⃣ CARICAMENTO DATI STL
# =========================
def load_stl_data(base_folder="dmodolomiti-turismo-veneto/stl-presenze-arrivi"):
    base_folder = _resolve_path(base_folder)
    stl_dolomiti = pd.DataFrame()
    stl_belluno = pd.DataFrame()

    for tipo in ["stl-dolomiti", "stl-belluno"]:
        folder = os.path.join(base_folder, tipo)
        frames = []
        if not os.path.exists(folder):
            continue
        for file in os.listdir(folder):
            if not file.endswith(".txt"):
                continue
            path = os.path.join(folder, file)
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")

            if not {"Mese", "Totale arrivi", "Totale presenze"}.issubset(df.columns):
                continue

            df = df.rename(columns={"Mese": "mese", "Totale arrivi": "arrivi", "Totale presenze": "presenze"})
            year = "".join([c for c in file if c.isdigit()])
            df["anno"] = int(year) if year else None
            frames.append(df[["anno", "mese", "arrivi", "presenze"]])

        if frames:
            if tipo == "stl-dolomiti":
                stl_dolomiti = pd.concat(frames, ignore_index=True)
            else:
                stl_belluno = pd.concat(frames, ignore_index=True)

    return stl_dolomiti, stl_belluno
