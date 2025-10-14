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

def load_provincia_belluno(data_folder="dati-provincia-annuali"):
    """
    Carica i file provinciali (es. presenze-arrivi-provincia-belluno-2024.txt)
    con colonne: mese, arrivi italiani/stranieri, presenze, totali, ecc.
    Restituisce un DataFrame aggregato per mese e anno.
    """
    import os
    import pandas as pd
    import glob

    ordine_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                   "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
    abbrev = {"Gennaio": "Gen", "Febbraio": "Feb", "Marzo": "Mar", "Aprile": "Apr",
              "Maggio": "Mag", "Giugno": "Giu", "Luglio": "Lug", "Agosto": "Ago",
              "Settembre": "Set", "Ottobre": "Ott", "Novembre": "Nov", "Dicembre": "Dic"}

    frames = []
    matches = glob.glob(os.path.join(os.getcwd(), "**", "presenze-arrivi-provincia-belluno*.txt"), recursive=True)

    if not matches:
        print("⚠️ Nessun file provinciale trovato.")
        return pd.DataFrame()

    for path in matches:
        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # rinomina colonne principali
        rename_map = {
            "mese": "mese",
            "totale_arrivi": "arrivi",
            "totale_presenze": "presenze"
        }
        df.rename(columns=rename_map, inplace=True)

        # elimina eventuali righe totali
        df = df[~df["mese"].astype(str).str.upper().str.contains("TOTALE", na=False)]

        # normalizza mese e anno
        df["mese"] = df["mese"].replace(abbrev)
        df["mese"] = pd.Categorical(df["mese"], categories=list(abbrev.values()), ordered=True)
        df["anno"] = df["anno"].astype(int)

        # seleziona colonne chiave
        df = df[["anno", "mese", "arrivi", "presenze"]]

        frames.append(df)
        print(f"✅ File provinciale caricato: {os.path.basename(path)} ({len(df)} righe)")

    if not frames:
        print("⚠️ Nessun file valido trovato per Belluno.")
        return pd.DataFrame()

    df_belluno = pd.concat(frames, ignore_index=True)
    df_belluno = df_belluno.sort_values(["anno", "mese"])
    return df_belluno
