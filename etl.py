"""Caricamento del dataset turistico validato usato dalla dashboard Streamlit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_DATASET = "data/processed/movimento_turistico.csv"

MONTH_ABBREVIATIONS = {
    1: "Gen",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mag",
    6: "Giu",
    7: "Lug",
    8: "Ago",
    9: "Set",
    10: "Ott",
    11: "Nov",
    12: "Dic",
}

REQUIRED_COLUMNS = {
    "anno",
    "mese_num",
    "ambito",
    "territorio_codice",
    "territorio",
    "provenienza",
    "arrivi",
    "presenze",
}


def _resolve_path(relative_path: str | Path) -> Path:
    """Restituisce un percorso assoluto relativo alla cartella dell'app."""
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parent / path


def _load_validated_data(data_path: str | Path = DEFAULT_DATASET) -> pd.DataFrame:
    """Legge e controlla lo schema minimo del dataset pubblicato dalla pipeline."""
    path = _resolve_path(data_path)
    if not path.exists():
        return pd.DataFrame()

    data = pd.read_csv(path, dtype={"territorio_codice": "string"})
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Dataset validato privo delle colonne richieste: {missing}")

    data = data.copy()
    data["anno"] = pd.to_numeric(data["anno"], errors="raise").astype(int)
    data["mese_num"] = pd.to_numeric(data["mese_num"], errors="raise").astype(int)
    data["arrivi"] = pd.to_numeric(data["arrivi"], errors="raise").astype(int)
    data["presenze"] = pd.to_numeric(data["presenze"], errors="raise").astype(int)
    data["mese"] = data["mese_num"].map(MONTH_ABBREVIATIONS)

    if data["mese"].isna().any():
        invalid_months = sorted(data.loc[data["mese"].isna(), "mese_num"].unique())
        raise ValueError(f"Numeri di mese non validi nel dataset: {invalid_months}")

    return data


def _totals_for_scope(data: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Seleziona le righe totali evitando duplicazioni per provenienza."""
    return data[
        data["ambito"].astype(str).str.upper().eq(scope)
        & data["provenienza"].astype(str).str.casefold().eq("totale")
    ].copy()


def load_dati_comunali(data_path: str | Path = DEFAULT_DATASET) -> pd.DataFrame:
    """Restituisce arrivi e presenze mensili dei Comuni nel formato della dashboard."""
    data = _load_validated_data(data_path)
    if data.empty:
        return pd.DataFrame()

    comuni = _totals_for_scope(data, "COMUNE").rename(
        columns={"territorio": "comune"}
    )
    return (
        comuni[["anno", "mese_num", "mese", "comune", "arrivi", "presenze"]]
        .sort_values(["anno", "comune", "mese_num"])
        .reset_index(drop=True)
    )


def load_provincia_belluno(data_path: str | Path = DEFAULT_DATASET) -> pd.DataFrame:
    """Restituisce i totali mensili della Provincia di Belluno."""
    data = _load_validated_data(data_path)
    if data.empty:
        return pd.DataFrame()

    provincia = _totals_for_scope(data, "PROVINCIA")
    provincia = provincia[
        provincia["territorio_codice"].astype(str).str.upper().eq("BL")
        | provincia["territorio"].astype(str).str.casefold().eq("belluno")
    ]
    return (
        provincia[["anno", "mese_num", "mese", "arrivi", "presenze"]]
        .sort_values(["anno", "mese_num"])
        .reset_index(drop=True)
    )


def load_stl_data(
    data_path: str | Path = DEFAULT_DATASET,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Restituisce, nell'ordine, STL Dolomiti e STL Belluno-Feltre-Alpago."""
    data = _load_validated_data(data_path)
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    stl = _totals_for_scope(data, "STL")
    codes = stl["territorio_codice"].astype(str).str.zfill(2)
    names = stl["territorio"].astype(str).str.casefold()

    dolomiti = stl[(codes == "01") | names.eq("dolomiti")]
    belluno = stl[(codes == "02") | names.str.contains("belluno", na=False)]

    columns = ["anno", "mese_num", "mese", "arrivi", "presenze"]
    dolomiti = dolomiti[columns].sort_values(["anno", "mese_num"]).reset_index(drop=True)
    belluno = belluno[columns].sort_values(["anno", "mese_num"]).reset_index(drop=True)
    return dolomiti, belluno
