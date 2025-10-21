import os
import pandas as pd

# =========================
# 1️⃣ DATI COMUNALI
# =========================
def load_dati_comunali(data_folder="dolomiti-turismo-veneto/dati-mensili-per-comune"):
    """
    Carica i file comunali (es. turismo-per-mese-comune-2024-presenze.txt)
    e li trasforma in un unico DataFrame normalizzato in formato lungo.
    """
    import os
    import pandas as pd

    frames = []
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]

    if not os.path.exists(data_folder):
        print(f"❌ Cartella non trovata: {data_folder}")
        return pd.DataFrame()

    for file in os.listdir(data_folder):
        if not file.endswith(".txt"):
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
            print(f"⚠️ Errore lettura {file}: {e}")
            continue

        # Normalizza intestazioni
        df.columns = [c.strip() for c in df.columns]

        # Estrai anno dal nome file
        year = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(year) if year else None

        # Colonna Comune
        comune_col = None
        for c in df.columns:
            if "comune" in c.lower():
                comune_col = c
                break
        if not comune_col:
            print(f"⚠️ Nessuna colonna 'comune' trovata in {file}")
            continue

        df.rename(columns={comune_col: "comune"}, inplace=True)

        # Colonne mese (tipo 'Gen Presenze', 'Feb Presenze', ecc.)
        month_cols = [c for c in df.columns if any(m in c for m in ordine_mesi)]
        if not month_cols:
            print(f"⚠️ Nessuna colonna mese trovata in {file}")
            continue

        # Trasformazione in formato lungo
        df_long = df.melt(
            id_vars=["anno", "comune"],
            value_vars=month_cols,
            var_name="mese",
            value_name="presenze"
        )

        # Pulisci nome mese (primi 3 caratteri)
        df_long["mese"] = df_long["mese"].str.extract(r"(^\w{3})")[0]
        df_long["mese"] = df_long["mese"].str.capitalize()
        df_long["mese"] = pd.Categorical(df_long["mese"], categories=ordine_mesi, ordered=True)

        # Converti a numerico
        df_long["presenze"] = pd.to_numeric(df_long["presenze"], errors="coerce").fillna(0)

        frames.append(df_long)

    if not frames:
        print("⚠️ Nessun file comunale valido caricato.")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "mese", "comune"])
    print(f"✅ Caricati {len(data):,} record da {len(frames)} file comunali.")
    return data

# =========================
# 2️⃣ DATI PROVINCIALI (BELLUNO)
# =========================
def load_provincia_belluno(data_folder="dolomiti-turismo-veneto/dati-provincia-annuali"):
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
        print(f"⚠️ Nessun file valido in {data_folder}")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    print(f"✅ Dati provinciali caricati: {len(data)} righe, {data['anno'].nunique()} anni.")
    return data


# =========================
# 3️⃣ DATI STL (Dolomiti e Belluno)
# =========================
def load_stl_data(base_folder="dolomiti-turismo-veneto/stl-presenze-arrivi"):
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
            print(f"⚠️ Nessun file valido in {path_dir}")
            return pd.DataFrame()

        data = pd.concat(frames, ignore_index=True)
        print(f"✅ Dati STL {subfolder} caricati: {len(data)} righe, {data['anno'].nunique()} anni.")
        return data

    stl_dolomiti = _load_stl_subfolder("stl-dolomiti")
    stl_belluno = _load_stl_subfolder("stl-belluno")
    return stl_dolomiti, stl_belluno
