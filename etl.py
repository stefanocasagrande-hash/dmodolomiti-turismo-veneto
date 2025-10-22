import os
import pandas as pd

# =========================
# 1️⃣ DATI COMUNALI
# =========================
def load_dati_comunali(folder_path="dolomiti-turismo-veneto/dati-mensili-per-comune"):
    """
    Carica i file dei dati comunali (turismo-per-mese-comune-*.txt)
    e li combina in un unico DataFrame normalizzato.
    """
    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    if not os.path.exists(folder_path):
        print(f"⚠️ Cartella non trovata: {folder_path}")
        return pd.DataFrame()

    for file in os.listdir(folder_path):
        if not file.endswith(".txt"):
            continue

        path = os.path.join(folder_path, file)
        try:
            if os.path.getsize(path) == 0:
                continue

            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except Exception as e:
            print(f"⚠️ Errore lettura {file}: {e}")
            continue

        if df.empty or "Comuni" not in df.columns:
            continue

        # Normalizza colonne
        df.columns = [c.strip().lower() for c in df.columns]
        anno = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(anno) if anno else None

        # Ricostruisci struttura mese → valore
        mesi_colonne = [c for c in df.columns if "presenze" in c]
        df_long = df.melt(
            id_vars=["anno", "comuni"],
            value_vars=mesi_colonne,
            var_name="mese",
            value_name="presenze"
        )

        # Pulizia
        df_long["mese"] = (
            df_long["mese"].str.extract(r"(\w{3})")[0]
            .str.capitalize()
            .replace({"Gen": "Gen", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr", "Mag": "Mag",
                      "Giu": "Giu", "Lug": "Lug", "Ago": "Ago", "Set": "Set", "Ott": "Ott", "Nov": "Nov", "Dic": "Dic"})
        )
        df_long["mese"] = pd.Categorical(df_long["mese"], categories=ordine_mesi, ordered=True)
        df_long.rename(columns={"comuni": "comune"}, inplace=True)
        frames.append(df_long)

    if not frames:
        print("⚠️ Nessun file comunale valido trovato.")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.dropna(subset=["comune", "presenze"])
    data["presenze"] = data["presenze"].astype(float)
    data = data.sort_values(["anno", "mese", "comune"])
    return data


# =========================
# 2️⃣ DATI PROVINCIALI
# =========================
def load_provincia_belluno(folder_path="dolomiti-turismo-veneto/dati-provincia-annuali"):
    """
    Carica i dati provinciali (presenze-arrivi-provincia-belluno-*.txt)
    e li combina in un DataFrame con colonne standard: anno, mese, arrivi, presenze.
    """
    frames = []
    if not os.path.exists(folder_path):
        return pd.DataFrame()

    for file in os.listdir(folder_path):
        if not file.endswith(".txt"):
            continue

        path = os.path.join(folder_path, file)
        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except Exception:
            continue

        if df.empty or "Mese" not in df.columns:
            continue

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        anno = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(anno) if anno else None

        df["mese"] = df["mese"].str[:3].str.capitalize()
        df = df.rename(columns={"totale_arrivi": "arrivi", "totale_presenze": "presenze"})
        df = df[["anno", "mese", "arrivi", "presenze"]]
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "mese"])
    return data


# =========================
# 3️⃣ DATI STL (Dolomiti / Belluno)
# =========================
def load_stl_data(base_folder="dolomiti-turismo-veneto/stl-presenze-arrivi"):
    """
    Carica i dati STL per Dolomiti e Belluno.
    """
    def load_stl_subfolder(subfolder):
        folder_path = os.path.join(base_folder, subfolder)
        frames = []
        if not os.path.exists(folder_path):
            return pd.DataFrame()

        for file in os.listdir(folder_path):
            if not file.endswith(".txt"):
                continue
            path = os.path.join(folder_path, file)
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except Exception:
                continue

            if df.empty or "Mese" not in df.columns:
                continue

            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            anno = "".join([c for c in file if c.isdigit()])
            df["anno"] = int(anno) if anno else None
            df["mese"] = df["mese"].str[:3].str.capitalize()
            df = df.rename(columns={"totale_arrivi": "arrivi", "totale_presenze": "presenze"})
            df = df[["anno", "mese", "arrivi", "presenze"]]
            frames.append(df)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    stl_dolomiti = load_stl_subfolder("stl-dolomiti")
    stl_belluno = load_stl_subfolder("stl-belluno")
    return stl_dolomiti, stl_belluno
