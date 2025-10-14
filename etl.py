import os
import glob
import pandas as pd

def load_data(data_folder="dati-mensili-per-comune"):
    """
    Carica i file 'turismo-per-mese-comune-*.txt' con colonne mensili
    e li trasforma in formato lungo (mese, presenze).
    """
    import os
    import pandas as pd
    import glob

    ordine_mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
                   "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    frames = []

    # Trova i file giusti ovunque nel progetto
    matches = glob.glob(os.path.join(os.getcwd(), "**", "turismo-per-mese-comune*.txt"), recursive=True)

    if not matches:
        print("⚠️ Nessun file 'turismo-per-mese-comune' trovato.")
        return pd.DataFrame()

    for path in matches:
        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Verifica che ci siano colonne mensili
        mesi_colonne = [c for c in df.columns if any(mese.lower() in c for mese in
                         ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"])]
        if not mesi_colonne:
            print(f"⚠️ Nessuna colonna mensile trovata in {path}, saltato.")
            continue

        # Normalizza nome del comune
        if "comuni" in df.columns:
            df.rename(columns={"comuni": "comune"}, inplace=True)

        # Estrai solo i campi utili
        keep = ["anno", "comune"] + mesi_colonne
        df = df[keep]

        # Converte le colonne mensili in formato lungo
        df_long = df.melt(id_vars=["anno", "comune"],
                          value_vars=mesi_colonne,
                          var_name="mese",
                          value_name="presenze")

        # Normalizza nome del mese
        df_long["mese"] = df_long["mese"].str.extract(r"(\w+)")[0].str[:3].str.capitalize()
        df_long["mese"] = pd.Categorical(df_long["mese"], categories=ordine_mesi, ordered=True)

        # Pulisci valori
        df_long["presenze"] = pd.to_numeric(df_long["presenze"], errors="coerce").fillna(0).astype(int)
        df_long["comune"] = df_long["comune"].str.strip()

        frames.append(df_long)
        print(f"✅ File caricato: {os.path.basename(path)} ({len(df_long)} righe)")

    if not frames:
        print("❌ Nessun file comunale valido caricato.")
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
