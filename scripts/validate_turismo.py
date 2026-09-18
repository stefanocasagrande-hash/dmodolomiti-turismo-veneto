"""Validate the normalized Veneto tourism dataset before dashboard publication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from normalize_turismo import OUTPUT_COLUMNS


class ValidationError(RuntimeError):
    """Raised when publishing the processed dataset would be unsafe."""


UNIQUE_KEY = ["anno", "mese_num", "ambito", "territorio_codice", "provenienza"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _validate_totals(data: pd.DataFrame) -> None:
    aggregates = data[data["ambito"].isin(["PROVINCIA", "STL"])]
    group_key = ["anno", "mese_num", "ambito", "territorio_codice"]
    for key, group in aggregates.groupby(group_key, sort=False):
        indexed = group.set_index("provenienza")
        _require(
            set(indexed.index) == {"Italiani", "Stranieri", "Totale"},
            f"Provenienze incomplete per {key}",
        )
        for metric in ("arrivi", "presenze"):
            expected = int(indexed.loc["Italiani", metric]) + int(
                indexed.loc["Stranieri", metric]
            )
            actual = int(indexed.loc["Totale", metric])
            _require(expected == actual, f"Totale {metric} incoerente per {key}")


def _validate_stl_sum(data: pd.DataFrame) -> None:
    aggregates = data[data["ambito"].isin(["PROVINCIA", "STL"])]
    for (year, month, provenance), group in aggregates.groupby(
        ["anno", "mese_num", "provenienza"], sort=False
    ):
        province = group[
            (group["ambito"] == "PROVINCIA")
            & (group["territorio_codice"] == "BL")
        ]
        stl = group[group["ambito"] == "STL"]
        _require(len(province) == 1 and len(stl) == 2, f"Ambiti incompleti: {year}-{month}")
        for metric in ("arrivi", "presenze"):
            _require(
                int(province.iloc[0][metric]) == int(stl[metric].sum()),
                f"Somma STL diversa dalla Provincia per {metric}: {year}-{month}, {provenance}",
            )


def _validate_month_continuity(data: pd.DataFrame) -> None:
    group_key = ["anno", "ambito", "territorio_codice", "provenienza"]
    for key, group in data.groupby(group_key, sort=False):
        months = sorted(group["mese_num"].astype(int).tolist())
        _require(months == list(range(1, max(months) + 1)), f"Mesi non continui per {key}")


def _anomaly_records(data: pd.DataFrame) -> list[dict]:
    key = ["ambito", "territorio_codice", "provenienza", "mese_num"]
    ordered = data.sort_values(key + ["anno"]).copy()
    anomalies: list[dict] = []
    for metric in ("arrivi", "presenze"):
        previous = ordered.groupby(key)[metric].shift(1)
        delta = ordered[metric] - previous
        rate = delta / previous.replace(0, pd.NA)
        mask = (rate.abs() > 2.0) & (delta.abs() > 1_000)
        for index in ordered.index[mask.fillna(False)]:
            row = ordered.loc[index]
            anomalies.append(
                {
                    "anno": int(row["anno"]),
                    "mese_num": int(row["mese_num"]),
                    "ambito": row["ambito"],
                    "territorio_codice": str(row["territorio_codice"]),
                    "territorio": row["territorio"],
                    "provenienza": row["provenienza"],
                    "metrica": metric,
                    "valore": int(row[metric]),
                    "variazione_percentuale": round(float(rate.loc[index] * 100), 1),
                }
            )
    return anomalies[:100]


def validate_data(data: pd.DataFrame) -> dict:
    missing = set(OUTPUT_COLUMNS).difference(data.columns)
    _require(not missing, f"Colonne mancanti: {sorted(missing)}")
    _require(not data.empty, "Dataset vuoto")
    _require(not data[UNIQUE_KEY].duplicated().any(), "Chiavi duplicate nel dataset")
    _require(not data[["arrivi", "presenze"]].isna().any().any(), "Metriche mancanti")
    _require((data[["arrivi", "presenze"]] >= 0).all().all(), "Valori negativi")
    _require(data["mese_num"].between(1, 12).all(), "Mese fuori intervallo 1-12")
    _require(set(data["ambito"]) == {"PROVINCIA", "STL", "COMUNE"}, "Ambiti incompleti")
    _require(
        set(data.loc[data["ambito"] == "STL", "territorio_codice"]) == {"01", "02"},
        "STL Dolomiti o Belluno assente",
    )

    _validate_totals(data)
    _validate_stl_sum(data)
    _validate_month_continuity(data)
    anomalies = _anomaly_records(data)
    latest_year = int(data["anno"].max())
    latest_month = int(data.loc[data["anno"] == latest_year, "mese_num"].max())
    return {
        "status": "passed",
        "rows": int(len(data)),
        "years": sorted(int(year) for year in data["anno"].unique()),
        "latest_period": {"year": latest_year, "month": latest_month},
        "checks": [
            "schema",
            "unique_keys",
            "non_negative_values",
            "continuous_months",
            "italiani_plus_stranieri_equals_totale",
            "stl_sum_equals_belluno_province",
        ],
        "warnings": {
            "anomalies_over_200_percent_with_absolute_delta_over_1000": len(anomalies),
            "sample": anomalies,
        },
    }


def validate_file(input_path: Path, report_path: Path | None = None) -> dict:
    data = pd.read_csv(input_path, dtype={"territorio_codice": str})
    report = validate_data(data)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if not report_path.exists() or report_path.read_text(encoding="utf-8") != serialized:
            report_path.write_text(serialized, encoding="utf-8")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("data/processed/movimento_turistico.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("data/processed/validation_report.json")
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = validate_file(args.input, args.report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
