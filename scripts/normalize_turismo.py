"""Normalize raw Regione Veneto tourism CSVs into one analysis-ready dataset."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


MONTHS = {
    "gen": (1, "Gennaio"),
    "gennaio": (1, "Gennaio"),
    "feb": (2, "Febbraio"),
    "febbraio": (2, "Febbraio"),
    "mar": (3, "Marzo"),
    "marzo": (3, "Marzo"),
    "apr": (4, "Aprile"),
    "aprile": (4, "Aprile"),
    "mag": (5, "Maggio"),
    "maggio": (5, "Maggio"),
    "giu": (6, "Giugno"),
    "giugno": (6, "Giugno"),
    "lug": (7, "Luglio"),
    "luglio": (7, "Luglio"),
    "ago": (8, "Agosto"),
    "agosto": (8, "Agosto"),
    "set": (9, "Settembre"),
    "settembre": (9, "Settembre"),
    "ott": (10, "Ottobre"),
    "ottobre": (10, "Ottobre"),
    "nov": (11, "Novembre"),
    "novembre": (11, "Novembre"),
    "dic": (12, "Dicembre"),
    "dicembre": (12, "Dicembre"),
}

TERRITORY_METADATA = {
    "provincia_belluno.csv": ("PROVINCIA", "BL", "Belluno"),
    "stl_dolomiti.csv": ("STL", "01", "Dolomiti"),
    "stl_belluno.csv": ("STL", "02", "Belluno - Feltre - Alpago"),
}

OUTPUT_COLUMNS = [
    "anno",
    "mese_num",
    "mese",
    "ambito",
    "territorio_codice",
    "territorio",
    "provenienza",
    "arrivi",
    "presenze",
    "stato_dato",
    "fonte_url",
    "data_acquisizione_utc",
    "source_file",
]


class NormalizationError(RuntimeError):
    """Raised when an official source no longer matches the expected structure."""


def _canonical(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            frame = pd.read_csv(path, sep=";", dtype=str, encoding=encoding)
            frame.columns = [_canonical(column) for column in frame.columns]
            return frame
        except UnicodeDecodeError:
            continue
    raise NormalizationError(f"Codifica non riconosciuta: {path}")


def _integer(value: object, *, field: str, source: Path) -> int:
    if pd.isna(value):
        raise NormalizationError(f"Valore mancante in {field}: {source}")
    cleaned = re.sub(r"[^0-9-]", "", str(value))
    if not cleaned or cleaned == "-":
        raise NormalizationError(f"Valore non numerico in {field}: {value!r} ({source})")
    return int(cleaned)


def _source_metadata(path: Path, raw_root: Path, manifest: dict) -> tuple[str, str]:
    relative = path.relative_to(raw_root).as_posix()
    entry = manifest.get("files", {}).get(relative)
    if not entry:
        raise NormalizationError(f"File non registrato nel manifest: {relative}")
    return entry["source_url"], entry["acquired_at_utc"]


def _period_metadata(frame: pd.DataFrame, path: Path) -> tuple[int, int, str]:
    if "anno" not in frame.columns or frame.empty:
        raise NormalizationError(f"Colonna anno assente o file vuoto: {path}")
    label = str(frame.iloc[0]["anno"])
    match = re.search(r"(20\d{2})", label)
    if not match:
        raise NormalizationError(f"Anno non riconosciuto in {path}: {label!r}")
    year = int(match.group(1))
    period = re.search(r"periodo\s+\w+\s*-\s*([A-Za-z]+)", label, re.IGNORECASE)
    if period:
        month_key = _canonical(period.group(1))
        if month_key not in MONTHS:
            raise NormalizationError(f"Mese finale non riconosciuto in {path}: {month_key}")
        return year, MONTHS[month_key][0], "provvisorio"
    return year, 12, "definitivo"


def _normalize_movement_file(path: Path, raw_root: Path, manifest: dict) -> list[dict]:
    frame = _read_csv(path)
    required = {
        "anno",
        "mese",
        "arrivi italiani",
        "arrivi stranieri",
        "presenze italiani",
        "presenze stranieri",
        "totale arrivi",
        "totale presenze",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise NormalizationError(f"Colonne mancanti in {path}: {sorted(missing)}")

    year, last_month, status = _period_metadata(frame, path)
    scope, territory_code, territory = TERRITORY_METADATA[path.name]
    source_url, acquired_at = _source_metadata(path, raw_root, manifest)
    source_file = path.relative_to(raw_root).as_posix()
    rows: list[dict] = []

    for _, raw in frame.iterrows():
        month_key = _canonical(raw["mese"])
        if month_key.startswith("totale"):
            continue
        if month_key not in MONTHS:
            raise NormalizationError(f"Mese non riconosciuto in {path}: {raw['mese']!r}")
        month_number, month_name = MONTHS[month_key]
        if month_number > last_month:
            continue

        values = {
            "arrivi_italiani": _integer(raw["arrivi italiani"], field="arrivi italiani", source=path),
            "arrivi_stranieri": _integer(raw["arrivi stranieri"], field="arrivi stranieri", source=path),
            "presenze_italiani": _integer(raw["presenze italiani"], field="presenze italiani", source=path),
            "presenze_stranieri": _integer(raw["presenze stranieri"], field="presenze stranieri", source=path),
            "arrivi_totale": _integer(raw["totale arrivi"], field="totale arrivi", source=path),
            "presenze_totale": _integer(raw["totale presenze"], field="totale presenze", source=path),
        }
        if values["arrivi_italiani"] + values["arrivi_stranieri"] != values["arrivi_totale"]:
            raise NormalizationError(f"Totale arrivi incoerente: {path}, {month_name}")
        if values["presenze_italiani"] + values["presenze_stranieri"] != values["presenze_totale"]:
            raise NormalizationError(f"Totale presenze incoerente: {path}, {month_name}")

        for provenance, suffix in (
            ("Italiani", "italiani"),
            ("Stranieri", "stranieri"),
            ("Totale", "totale"),
        ):
            rows.append(
                {
                    "anno": year,
                    "mese_num": month_number,
                    "mese": month_name,
                    "ambito": scope,
                    "territorio_codice": territory_code,
                    "territorio": territory,
                    "provenienza": provenance,
                    "arrivi": values[f"arrivi_{suffix}"],
                    "presenze": values[f"presenze_{suffix}"],
                    "stato_dato": status,
                    "fonte_url": source_url,
                    "data_acquisizione_utc": acquired_at,
                    "source_file": source_file,
                }
            )
    return rows


def _commune_metric(path: Path, metric: str, last_month: int) -> pd.DataFrame:
    frame = _read_csv(path)
    if "comuni" not in frame.columns:
        raise NormalizationError(f"Colonna comuni assente: {path}")
    frame = frame[frame["comuni"].astype(str).str.match(r"^25\d{3}\s+-")].copy()
    if frame.empty:
        raise NormalizationError(f"Nessun comune bellunese trovato: {path}")

    id_columns = ["comuni"]
    month_columns: dict[str, tuple[int, str]] = {}
    for column in frame.columns:
        match = re.match(r"([a-z]{3})\s+(arrivi|presenze)$", column)
        if match and match.group(2) == metric and match.group(1) in MONTHS:
            month_columns[column] = MONTHS[match.group(1)]
    if len(month_columns) != 12:
        raise NormalizationError(
            f"Attese 12 colonne mensili {metric}, trovate {len(month_columns)}: {path}"
        )

    long = frame.melt(
        id_vars=id_columns,
        value_vars=list(month_columns),
        var_name="colonna_mese",
        value_name=metric,
    )
    long["mese_num"] = long["colonna_mese"].map(lambda value: month_columns[value][0])
    long["mese"] = long["colonna_mese"].map(lambda value: month_columns[value][1])
    long = long[long["mese_num"] <= last_month].copy()
    long[metric] = [
        _integer(value, field=metric, source=path) for value in long[metric]
    ]
    extracted = long["comuni"].str.extract(r"^(25\d{3})\s+-\s*(.+?)\s*$")
    long["territorio_codice"] = extracted[0]
    long["territorio"] = extracted[1]
    return long[["territorio_codice", "territorio", "mese_num", "mese", metric]]


def _normalize_communes(year_dir: Path, raw_root: Path, manifest: dict) -> list[dict]:
    province_path = year_dir / "provincia_belluno.csv"
    province = _read_csv(province_path)
    year, last_month, status = _period_metadata(province, province_path)
    arrivals_path = year_dir / "comuni_veneto_arrivi.csv"
    nights_path = year_dir / "comuni_veneto_presenze.csv"
    arrivals = _commune_metric(arrivals_path, "arrivi", last_month)
    nights = _commune_metric(nights_path, "presenze", last_month)

    key = ["territorio_codice", "territorio", "mese_num", "mese"]
    if set(map(tuple, arrivals[key].to_numpy())) != set(map(tuple, nights[key].to_numpy())):
        raise NormalizationError(
            f"I comuni disponibili per arrivi e presenze non coincidono nel {year}"
        )
    merged = arrivals.merge(nights, on=key, validate="one_to_one")
    arrivals_url, arrivals_acquired_at = _source_metadata(arrivals_path, raw_root, manifest)
    nights_url, nights_acquired_at = _source_metadata(nights_path, raw_root, manifest)
    source_url = f"{arrivals_url};{nights_url}"
    acquired_at = max(arrivals_acquired_at, nights_acquired_at)
    source_file = ";".join(
        [
            arrivals_path.relative_to(raw_root).as_posix(),
            nights_path.relative_to(raw_root).as_posix(),
        ]
    )
    rows: list[dict] = []
    for record in merged.to_dict("records"):
        rows.append(
            {
                "anno": year,
                "mese_num": record["mese_num"],
                "mese": record["mese"],
                "ambito": "COMUNE",
                "territorio_codice": record["territorio_codice"],
                "territorio": record["territorio"],
                "provenienza": "Totale",
                "arrivi": record["arrivi"],
                "presenze": record["presenze"],
                "stato_dato": status,
                "fonte_url": source_url,
                "data_acquisizione_utc": acquired_at,
                "source_file": source_file,
            }
        )
    return rows


def normalize_official_data(raw_root: Path, output_path: Path) -> pd.DataFrame:
    manifest_path = raw_root / "manifest.json"
    if not manifest_path.exists():
        raise NormalizationError(f"Manifest assente: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rows: list[dict] = []
    year_dirs = sorted(path for path in raw_root.iterdir() if path.is_dir() and path.name.isdigit())
    for year_dir in year_dirs:
        movement_files = [year_dir / name for name in TERRITORY_METADATA]
        commune_files = [
            year_dir / "comuni_veneto_arrivi.csv",
            year_dir / "comuni_veneto_presenze.csv",
        ]
        available = [path.exists() for path in movement_files + commune_files]
        if not any(available):
            continue
        if not all(available):
            missing = [str(path) for path, exists in zip(movement_files + commune_files, available) if not exists]
            raise NormalizationError(f"Fonti incomplete per {year_dir.name}: {missing}")
        for path in movement_files:
            rows.extend(_normalize_movement_file(path, raw_root, manifest))
        rows.extend(_normalize_communes(year_dir, raw_root, manifest))

    if not rows:
        raise NormalizationError("Nessun dato normalizzato")
    data = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    data = data.sort_values(
        ["anno", "ambito", "territorio_codice", "provenienza", "mese_num"]
    ).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = data.to_csv(index=False, lineterminator="\n")
    if not output_path.exists() or output_path.read_text(encoding="utf-8") != serialized:
        output_path.write_text(serialized, encoding="utf-8")
    return data


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root", type=Path, default=Path("data/raw/regione_veneto")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/movimento_turistico.csv")
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    data = normalize_official_data(args.raw_root, args.output)
    print(f"Normalizzate {len(data)} righe in {args.output}")


if __name__ == "__main__":
    main()
