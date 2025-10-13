import os
import glob
import pandas as pd

def find_files_recursive(pattern):
    """Restituisce la lista di file che matchano il pattern (ricorsivamente dalla cwd)."""
    cwd = os.getcwd()
    matches = glob.glob(os.path.join(cwd, "**", pattern), recursive=True)
    return matches

def load_data(data_folder=None):
    """
    Cerca ricorsivamente file 'turismo-per-mese-comune*.txt' sotto la working dir
    e li carica. Restituisce DataFrame concatenato.
    """
    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    frames = []

    # cerca ricorsivamente i file con quel pattern
    matches = find_files_recursive("turismo-per-mese-comune*.txt")

    print(f"DEBUG: cwd = {os.getcwd()}")
    print(f"DEBUG: file trovati per 'turismo-per-mese-comune': {matches}")

    for path in matches:
        file = os.path.basename(path)
        try:
            if os.path.getsize(path) == 0:
                print(f"⚠️ File vuoto saltato: {path}")
                continue
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")
            if df.empty:
                print(f"⚠️ File senza dati: {path}")
                continue
        except Exception as e:
            print(f"⚠️ Errore leggendo {path}: {e}")
            continue

        # normalizza colonne
        df.columns = [c.strip().lower() for c in df.columns]
        # estrai anno dal nome file (es. turismo-per-mese-comune-2023-presenze.txt)
        year = "".join([c for c in file if c.isdigit()])
        df["anno"] = int(year) if year else None

        # gestione colonne possibili
        if "comune" not in df.columns:
            if "comuni" in df.columns:
                df.rename(columns={"comuni": "comune"}, inplace=True)
            elif "denominazione_comune" in df.columns:
                df.rename(columns={"denominazione_comune": "comune"}, inplace=True)

        if "presenze" not in df.columns or "mese" not in df.columns:
            print(f"⚠️ Colonne mancanti in {path} (presenze/mese). Saltato.")
            continue

        df["mese"] = df["mese"].astype(str).str.strip().str[:3].str.capitalize()
        df["mese"] = pd.Categorical(df["mese"], categories=ordine_mesi, ordered=True)
        df = df.dropna(subset=["comune", "presenze"])
        print(f"✅ Caricato {path} -> righe: {len(df)}")
        frames.append(df)

    if not frames:
        print("❌ Nessun file valido trovato per i dati comunali.")
        return pd.DataFrame()

    data = pd.concat(frames, ignore_index=True)
    data = data.sort_values(["anno", "mese", "comune"])
    return data


def load_provincia_belluno(data_folder=None):
    """
    Cerca ricorsivamente file 'presenze-arrivi-provincia-belluno*.txt' e li carica.
    Restituisce DataFrame con colonne mese, anno, arrivi, presenze.
    """
    ordine_mesi_full = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    abbrev = {"Gennaio":"Gen","Febbraio":"Feb","Marzo":"Mar","Aprile":"Apr","Maggio":"Mag","Giugno":"Giu",
              "Luglio":"Lug","Agosto":"Ago","Settembre":"Set","Ottobre":"Ott","Novembre":"Nov","Dicembre":"Dic"}

    frames = []
    matches = find_files_recursive("presenze-arrivi-provincia-belluno*.txt")
    print(f"DEBUG: file trovati per 'presenze-arrivi-provincia-belluno': {matches}")

    for path in matches:
        file = os.path.basename(path)
        try:
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, sep=";", encoding="latin1")
            if df.empty:
                print(f"⚠️ File provinciale vuoto: {path}")
                continue
        except Exception as e:
            print(f"⚠️ Errore leggendo file provinciale {path}: {e}")
            continue

        df.columns = [c.strip().lower() for c in df.columns]
        # mappa possibili nomi colonne a standard
        rename_map = {}
        for c in df.columns:
            if "totale arrivi" in c:
                rename_map[c] = "arrivi"
            if "totale presenze" in c or "totale_presenze" in c:
                rename_map[c] = "presenze"
            if c == "mese":
                rename_map[c] = "mese"
            if c == "anno":
                rename_map[c] = "anno"
        df.rename(columns=rename_map, inplace=True)

        if "mese" not in df.columns or "arrivi" not in df.columns or "presenze" not in df.columns:
            print(f"⚠️ Colonne richieste non trovate in {path}, saltato.")
            continue

        # rimuovi eventuali righe di totale
        df = df[~df["mese"].astype(str).str.upper().str.contains("TOTALE", na=False)]

        # anno: preferisci colonna, altrimenti estrai dal nome file
        if "anno" in df.columns:
            try:
                df["anno"] = df["anno"].astype(str).str.extract(r"(\d{4})").astype(float).astype("Int64")
            except Exception:
                df["anno"] = None
        else:
            year = "".join([c for c in file if c.isdigit()])
            df["anno"] = int(year) if year else None

        # normalizza mese (da "Gennaio" a "Gen")
        df["mese"] = df["mese"].astype(str).str.strip().replace(abbrev)
        df["mese"] = pd.Categorical(df["mese"], categories=list(abbrev.values()), ordered=True)

        df = df[["mese", "anno", "arrivi", "presenze"]]
        frames.append(df)
        print(f"✅ Caricato provinciale: {path} -> righe: {len(df)}")

    if not frames:
        print("❌ Nessun file provinciale valido trovato.")
        return pd.DataFrame()

    df_belluno = pd.concat(frames, ignore_index=True).sort_values(["anno", "mese"])
    return df_belluno
