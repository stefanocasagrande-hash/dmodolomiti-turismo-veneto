"""Acquire monthly foreign-market presences from Regione Veneto.

The official ``barre.jsp`` view exposes one monthly series for every foreign
market and STL.  This module downloads the two Belluno STLs, validates the
series and derives the Province of Belluno as their sum.
"""

from __future__ import annotations

import html
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests


BASE_URL = "https://statistica.regione.veneto.it/jsp/barre.jsp"
USER_AGENT = (
    "DMO-Dolomiti-Bellunesi-data-pipeline/1.0 "
    "(+https://github.com/stefanocasagrande-hash/dmodolomiti-turismo-veneto)"
)

TERRITORIES = {
    "STL_DOLOMITI": {
        "query": "01_Dolomiti-Cortina",
        "label": "STL Dolomiti",
    },
    "STL_BELLUNO": {
        "query": "02_Belluno",
        "label": "STL Belluno",
    },
}

MONTH_NUMBER = {
    "Gen": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "Mag": 5,
    "Giu": 6,
    "Lug": 7,
    "Ago": 8,
    "Set": 9,
    "Ott": 10,
    "Nov": 11,
    "Dic": 12,
}
MONTH_NAME = {
    1: "Gennaio",
    2: "Febbraio",
    3: "Marzo",
    4: "Aprile",
    5: "Maggio",
    6: "Giugno",
    7: "Luglio",
    8: "Agosto",
    9: "Settembre",
    10: "Ottobre",
    11: "Novembre",
    12: "Dicembre",
}

MARKET_ALIASES = {
    "Gran Bretagna": "Regno Unito",
    "Rep. Ceca": "Repubblica Ceca",
    "U.S.A.": "Stati Uniti",
    "Paesi bassi": "Paesi Bassi",
    "Svizzera-Liecht.": "Svizzera-Liechtenstein",
}

MARKET_OPTION_RE = re.compile(
    r'<option\s+value="(?P<value>\d+_[^"]+)"[^>]*>(?P<label>[^<]+)</option>',
    flags=re.IGNORECASE,
)
MARKET_SELECT_RE = re.compile(
    r'<select[^>]+name="stato"[^>]*>(?P<body>.*?)</select>',
    flags=re.IGNORECASE | re.DOTALL,
)
SERIES_RE = re.compile(
    r'title="\((?P<year>20\d{2}),\s*(?P<month>[A-Z][a-z]{2})\)\s*=\s*'
    r'(?P<value>[\d.]+)"',
    flags=re.IGNORECASE,
)


class MarketDownloadError(RuntimeError):
    """Raised when the official market series is unavailable or malformed."""


def _get_text(url: str, *, timeout: int = 60, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            return response.content.decode("cp1252", errors="replace")
        except requests.RequestException as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(2**attempt)
    raise MarketDownloadError(
        f"Download mercati fallito dopo {attempts} tentativi: {url}"
    ) from last_error


def build_url(territory: str, market: str, current_year: int) -> str:
    query = urlencode({
        'anno': current_year,
        'territorio': territory,
        'stato': market,
        'tipo': 'Presenze',
    })
    return f"{BASE_URL}?{query}"


def discover_markets(page: str) -> list[tuple[str, str]]:
    """Return official market option values and human-readable labels."""

    select = MARKET_SELECT_RE.search(page)
    if not select:
        raise MarketDownloadError(
            "La pagina regionale non contiene il selettore dei mercati esteri"
        )

    markets: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in MARKET_OPTION_RE.finditer(select.group("body")):
        value = html.unescape(match.group("value")).strip()
        label = html.unescape(match.group("label")).strip()
        if value.startswith(("99_", "98_")) or value in seen:
            continue
        if value.startswith("97_"):
            label = "Totale stranieri"
        else:
            label = MARKET_ALIASES.get(label, label)
        seen.add(value)
        markets.append((value, label))

    if not markets or not any(value.startswith("97_") for value, _ in markets):
        raise MarketDownloadError(
            "La pagina regionale non contiene l'elenco atteso dei mercati esteri"
        )
    return markets


def parse_monthly_series(
    page: str,
    *,
    territory_code: str,
    territory: str,
    market_code: str,
    market: str,
    source_url: str,
    start_year: int,
    current_year: int,
) -> list[dict[str, object]]:
    """Parse chart tooltips into a normalized monthly time series."""

    values: dict[tuple[int, int], int] = {}
    for match in SERIES_RE.finditer(page):
        year = int(match.group("year"))
        month_token = match.group("month").title()
        if year < start_year or month_token not in MONTH_NUMBER:
            continue
        month = MONTH_NUMBER[month_token]
        value = int(match.group("value").replace(".", ""))
        values[(year, month)] = value

    if not values:
        raise MarketDownloadError(
            f"Nessun valore mensile trovato per {territory} / {market}"
        )

    market_type = (
        "Totale estero"
        if market_code.startswith("97_")
        else "Aggregato"
        if market.lower().startswith("altri")
        else "Paese"
    )
    return [
        {
            "anno": year,
            "mese_num": month,
            "mese": MONTH_NAME[month],
            "ambito": "STL",
            "territorio_codice": territory_code,
            "territorio": territory,
            "mercato_codice": market_code.split("_", 1)[0],
            "mercato": market,
            "mercato_tipo": market_type,
            "presenze": value,
            "stato_dato": "provvisorio" if year == current_year else "definitivo",
            "fonte_url": source_url,
        }
        for (year, month), value in sorted(values.items())
    ]


def _download_series(
    territory_code: str,
    territory_query: str,
    territory_label: str,
    market_code: str,
    market_label: str,
    start_year: int,
    current_year: int,
) -> list[dict[str, object]]:
    url = build_url(territory_query, market_code, current_year)
    page = _get_text(url)
    return parse_monthly_series(
        page,
        territory_code=territory_code,
        territory=territory_label,
        market_code=market_code,
        market=market_label,
        source_url=url,
        start_year=start_year,
        current_year=current_year,
    )


def _remove_future_months(df: pd.DataFrame) -> pd.DataFrame:
    totals = df[df["mercato_tipo"] == "Totale estero"]
    active = set(
        totals.loc[totals["presenze"] > 0, ["territorio_codice", "anno", "mese_num"]]
        .itertuples(index=False, name=None)
    )
    keys = list(
        zip(df["territorio_codice"], df["anno"], df["mese_num"], strict=False)
    )
    return df[[key in active for key in keys]].copy()


def _derive_province(df: pd.DataFrame) -> pd.DataFrame:
    group_columns = [
        "anno",
        "mese_num",
        "mese",
        "mercato_codice",
        "mercato",
        "mercato_tipo",
        "stato_dato",
    ]
    province = df.groupby(group_columns, as_index=False, observed=True)["presenze"].sum()
    province["ambito"] = "PROVINCIA"
    province["territorio_codice"] = "BL"
    province["territorio"] = "Provincia di Belluno (DMO)"
    province["fonte_url"] = "Somma delle serie ufficiali STL Dolomiti e STL Belluno"
    return province[df.columns]


def validate_market_data(df: pd.DataFrame) -> dict[str, object]:
    key = ["anno", "mese_num", "territorio_codice", "mercato_codice"]
    duplicates = int(df.duplicated(key).sum())
    negatives = int((df["presenze"] < 0).sum())
    missing = int(df[key + ["presenze"]].isna().sum().sum())

    incomplete_series: list[dict[str, object]] = []
    for territory_code, territory in df.groupby("territorio_codice", observed=True):
        expected_periods = set(
            territory.loc[
                territory["mercato_tipo"] == "Totale estero", ["anno", "mese_num"]
            ].itertuples(index=False, name=None)
        )
        for market_code, series in territory.groupby("mercato_codice", observed=True):
            actual_periods = set(
                series[["anno", "mese_num"]].itertuples(index=False, name=None)
            )
            if actual_periods != expected_periods:
                incomplete_series.append(
                    {
                        "territorio_codice": territory_code,
                        "mercato_codice": market_code,
                        "mesi_attesi": len(expected_periods),
                        "mesi_presenti": len(actual_periods),
                    }
                )

    mismatches: list[dict[str, object]] = []
    for keys, group in df.groupby(
        ["territorio_codice", "anno", "mese_num"], observed=True
    ):
        total = group.loc[group["mercato_tipo"] == "Totale estero", "presenze"]
        components = group.loc[group["mercato_tipo"] != "Totale estero", "presenze"].sum()
        if len(total) != 1 or int(total.iloc[0]) != int(components):
            mismatches.append(
                {
                    "territorio_codice": keys[0],
                    "anno": int(keys[1]),
                    "mese_num": int(keys[2]),
                    "totale_dichiarato": int(total.iloc[0]) if len(total) else None,
                    "somma_mercati": int(components),
                }
            )

    if duplicates or negatives or missing or incomplete_series or mismatches:
        raise MarketDownloadError(
            "Validazione mercati fallita: "
            f"duplicati={duplicates}, negativi={negatives}, mancanti={missing}, "
            f"serie_incomplete={len(incomplete_series)}, "
            f"totali_non_coerenti={len(mismatches)}"
        )
    return {
        "status": "ok",
        "rows": int(len(df)),
        "years": sorted(int(year) for year in df["anno"].unique()),
        "latest_period": {
            "year": int(df["anno"].max()),
            "month": int(df.loc[df["anno"] == df["anno"].max(), "mese_num"].max()),
        },
    }


def fetch_foreign_market_data(
    output: Path,
    *,
    start_year: int = 2020,
    current_year: int | None = None,
    max_workers: int = 8,
) -> dict[str, object]:
    """Download, validate and write the normalized market dataset."""

    current_year = current_year or datetime.now().year
    discovery_url = build_url(
        TERRITORIES["STL_DOLOMITI"]["query"],
        "97_TOTALE STRANIERI",
        current_year,
    )
    markets = discover_markets(_get_text(discovery_url))

    jobs = [
        (
            territory_code,
            territory_info["query"],
            territory_info["label"],
            market_code,
            market_label,
        )
        for territory_code, territory_info in TERRITORIES.items()
        for market_code, market_label in markets
    ]
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(
                _download_series,
                territory_code,
                territory_query,
                territory_label,
                market_code,
                market_label,
                start_year,
                current_year,
            ): (territory_label, market_label)
            for (
                territory_code,
                territory_query,
                territory_label,
                market_code,
                market_label,
            ) in jobs
        }
        for future in as_completed(futures):
            territory_label, market_label = futures[future]
            try:
                rows.extend(future.result())
            except Exception as exc:  # report every failed market before aborting
                errors.append(f"{territory_label} / {market_label}: {exc}")

    if errors:
        raise MarketDownloadError(
            "Download incompleto; nessun dato e' stato pubblicato. " + " | ".join(errors)
        )

    df = pd.DataFrame(rows)
    df = _remove_future_months(df)
    df = pd.concat([df, _derive_province(df)], ignore_index=True)
    df = df.sort_values(
        ["anno", "mese_num", "territorio_codice", "mercato_tipo", "mercato"]
    ).reset_index(drop=True)
    validation = validate_market_data(df)

    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = df.to_csv(index=False, lineterminator="\n")
    changed = not output.exists() or output.read_text(encoding="utf-8") != serialized
    if changed:
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(output)

    return {
        "downloaded_series": len(jobs),
        "markets": len(markets),
        "changed": changed,
        "output": str(output),
        "validation": validation,
    }

