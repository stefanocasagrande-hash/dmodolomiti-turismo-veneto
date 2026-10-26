"""Loading and analytical helpers for the foreign-markets dashboard."""

from __future__ import annotations

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd


MONTHS = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]
WINTER_MONTHS = [12, 1, 2, 3]


def load_data(data_dir="dati-paesi-di-provenienza", prefix="presenze-dolomiti-estero"):
    """Load the legacy wide files kept as a deployment fallback."""

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"La cartella '{data_dir}' non esiste.")
    all_files = sorted(glob.glob(os.path.join(data_dir, f"{prefix}-*.txt")))
    if not all_files:
        raise FileNotFoundError(
            f"Nessun file trovato in '{data_dir}' con prefisso '{prefix}-'."
        )

    frames = []
    for file in all_files:
        year = int(os.path.basename(file).split("-")[-1].split(".")[0])
        frame = pd.read_csv(file, sep=";", header=1, engine="python")
        month_column = next(
            (column for column in frame.columns if "MESE" in column.upper()),
            frame.columns[0],
        )
        frame.rename(columns={month_column: "Mese"}, inplace=True)
        frame["Anno"] = year
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    long = data.melt(
        id_vars=["Mese", "Anno"], var_name="Paese", value_name="Presenze"
    )
    long["Presenze"] = (
        pd.to_numeric(long["Presenze"], errors="coerce").fillna(0).astype(int)
    )
    long["Paese"] = (
        long["Paese"].astype(str).str.replace(" Paese", "", regex=False).str.strip()
    )
    long["Mese"] = (
        long["Mese"].astype(str).str.replace(r"^\d+", "", regex=True).str.strip()
    )
    long["Mese"] = pd.Categorical(long["Mese"], categories=MONTHS, ordered=True)
    return long[long["Mese"].notna() & long["Paese"].notna()]


def _legacy_to_normalized(legacy: pd.DataFrame) -> pd.DataFrame:
    normalized = legacy.rename(
        columns={
            "Anno": "anno", "Mese": "mese", "Paese": "mercato", "Presenze": "presenze",
        }
    ).copy()
    normalized["mese"] = normalized["mese"].astype(str)
    normalized["mese_num"] = normalized["mese"].map(
        {name: number for number, name in enumerate(MONTHS, start=1)}
    )
    normalized["ambito"] = "STL"
    normalized["territorio_codice"] = "STL_DOLOMITI"
    normalized["territorio"] = "STL Dolomiti"
    normalized["mercato_codice"] = normalized["mercato"]
    normalized["mercato_tipo"] = np.select(
        [
            normalized["mercato"].str.contains("Totale stranieri", case=False),
            normalized["mercato"].str.startswith("Altri", na=False),
        ],
        ["Totale estero", "Aggregato"],
        default="Paese",
    )
    normalized["stato_dato"] = "archivio"
    normalized["fonte_url"] = "Archivio storico Regione Veneto"
    columns = [
        "anno", "mese_num", "mese", "ambito", "territorio_codice", "territorio",
        "mercato_codice", "mercato", "mercato_tipo", "presenze", "stato_dato", "fonte_url",
    ]
    return normalized[columns]


def load_market_data(
    processed_file: str | Path,
    legacy_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, str]:
    """Load the automated dataset, falling back to the legacy STL archive."""

    processed_path = Path(processed_file)
    if processed_path.exists():
        data = pd.read_csv(processed_path)
        source = "automatico"
    elif legacy_dir is not None:
        data = _legacy_to_normalized(load_data(str(legacy_dir)))
        source = "archivio"
    else:
        raise FileNotFoundError("Dataset dei mercati esteri non trovato")

    for column in ["anno", "mese_num", "presenze"]:
        data[column] = pd.to_numeric(data[column], errors="raise").astype(int)
    data["mese"] = pd.Categorical(data["mese"], categories=MONTHS, ordered=True)
    return data, source


def real_markets(data: pd.DataFrame) -> pd.DataFrame:
    """Exclude totals and residual geographic aggregates."""

    return data[data["mercato_tipo"] == "Paese"].copy()


def latest_comparable_period(
    data: pd.DataFrame, territory: str
) -> tuple[int, int, list[int]]:
    """Return latest year, comparison year and active months common to both."""

    subset = data[
        (data["territorio"] == territory)
        & (data["mercato_tipo"] == "Totale estero")
        & (data["presenze"] > 0)
    ]
    years = sorted(int(year) for year in subset["anno"].unique())
    if len(years) < 2:
        raise ValueError("Servono almeno due anni confrontabili")
    latest, previous = years[-1], years[-2]
    latest_months = set(subset.loc[subset["anno"] == latest, "mese_num"])
    previous_months = set(subset.loc[subset["anno"] == previous, "mese_num"])
    months = sorted(int(month) for month in latest_months & previous_months)
    if not months:
        raise ValueError("Nessun mese confrontabile tra gli ultimi due anni")
    return latest, previous, months


def annual_market_comparison(
    data: pd.DataFrame, territory: str
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Compare foreign markets over the same active months of the last two years."""

    latest, previous, months = latest_comparable_period(data, territory)
    subset = real_markets(data)
    subset = subset[
        (subset["territorio"] == territory)
        & (subset["anno"].isin([previous, latest]))
        & (subset["mese_num"].isin(months))
    ]
    pivot = subset.pivot_table(
        index="mercato", columns="anno", values="presenze", aggfunc="sum", fill_value=0
    ).reset_index()
    pivot["differenza"] = pivot[latest] - pivot[previous]
    pivot["variazione_pct"] = np.where(
        pivot[previous] > 0, pivot["differenza"] / pivot[previous] * 100, np.nan
    )

    total_rows = data[
        (data["territorio"] == territory)
        & (data["mercato_tipo"] == "Totale estero")
        & (data["anno"].isin([previous, latest]))
        & (data["mese_num"].isin(months))
    ]
    totals = total_rows.groupby("anno")["presenze"].sum()
    latest_total = int(totals.get(latest, 0))
    previous_total = int(totals.get(previous, 0))
    total_delta = latest_total - previous_total
    pivot["quota_pct"] = pivot[latest] / latest_total * 100 if latest_total else np.nan
    pivot["contributo_crescita_pct"] = (
        pivot["differenza"] / total_delta * 100 if total_delta else np.nan
    )
    pivot = pivot.sort_values(latest, ascending=False).reset_index(drop=True)
    metadata = {
        "latest": latest, "previous": previous, "months": months,
        "latest_total": latest_total, "previous_total": previous_total,
        "total_delta": total_delta,
    }
    return pivot, metadata


def add_winter_season(data: pd.DataFrame) -> pd.DataFrame:
    """Attach a December-March winter label to every relevant row."""

    winter = data[data["mese_num"].isin(WINTER_MONTHS)].copy()
    winter["stagione_inizio"] = np.where(
        winter["mese_num"] == 12, winter["anno"], winter["anno"] - 1
    ).astype(int)
    winter["stagione"] = winter["stagione_inizio"].map(
        lambda year: f"{year}/{str(year + 1)[-2:]}"
    )
    return winter


def complete_winter_seasons(data: pd.DataFrame, territory: str) -> list[str]:
    winter = add_winter_season(data)
    totals = winter[
        (winter["territorio"] == territory)
        & (winter["mercato_tipo"] == "Totale estero")
        & (winter["presenze"] > 0)
    ]
    complete = (
        totals.groupby(["stagione_inizio", "stagione"])["mese_num"]
        .nunique()
        .reset_index(name="mesi")
    )
    return complete.loc[complete["mesi"] == 4].sort_values("stagione_inizio")["stagione"].tolist()


def winter_market_comparison(
    data: pd.DataFrame,
    territory: str,
    *,
    seasons_count: int = 3,
    top_n: int = 7,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Build a top-market comparison over the latest complete winters."""

    seasons = complete_winter_seasons(data, territory)[-seasons_count:]
    if len(seasons) < 2:
        raise ValueError("Non sono disponibili almeno due inverni completi")

    winter = add_winter_season(data)
    actual = real_markets(winter)
    actual = actual[
        (actual["territorio"] == territory) & (actual["stagione"].isin(seasons))
    ]
    pivot = actual.pivot_table(
        index="mercato", columns="stagione", values="presenze", aggfunc="sum", fill_value=0,
    )
    latest, previous = seasons[-1], seasons[-2]
    pivot = pivot.sort_values(latest, ascending=False).head(top_n).reset_index()

    totals = (
        winter[
            (winter["territorio"] == territory)
            & (winter["mercato_tipo"] == "Totale estero")
            & (winter["stagione"].isin(seasons))
        ]
        .groupby("stagione")["presenze"].sum().reindex(seasons)
    )
    pivot["differenza"] = pivot[latest] - pivot[previous]
    pivot["variazione_pct"] = np.where(
        pivot[previous] > 0, pivot["differenza"] / pivot[previous] * 100, np.nan
    )
    pivot["quota_pct"] = pivot[latest] / totals[latest] * 100
    total_delta = totals[latest] - totals[previous]
    pivot["contributo_crescita_pct"] = (
        pivot["differenza"] / total_delta * 100 if total_delta else np.nan
    )
    return pivot, totals, seasons
