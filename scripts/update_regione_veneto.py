"""Run download, normalization and validation as one safe update transaction."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from fetch_regione_veneto import fetch_official_data
from normalize_turismo import normalize_official_data
from validate_turismo import validate_file


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=None,
        help=(
            "Anni da aggiornare. Senza argomento scarica dal 2021 al presente al "
            "primo avvio, poi aggiorna anno corrente e precedente."
        ),
    )
    parser.add_argument(
        "--raw-root", type=Path, default=Path("data/raw/regione_veneto")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/processed/movimento_turistico.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("data/processed/validation_report.json")
    )
    parser.add_argument("--skip-summary", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    current_year = datetime.now().year
    manifest_path = args.raw_root / "manifest.json"
    years = (
        args.years
        if args.years
        else (
            [current_year - 1, current_year]
            if manifest_path.exists()
            else list(range(2021, current_year + 1))
        )
    )
    fetch_result = fetch_official_data(
        years,
        args.raw_root,
        include_summary=not args.skip_summary,
    )
    normalize_official_data(args.raw_root, args.output)
    validation = validate_file(args.output, args.report)
    summary = {
        "fetch": fetch_result,
        "validation": {
            "status": validation["status"],
            "rows": validation["rows"],
            "years": validation["years"],
            "latest_period": validation["latest_period"],
            "anomaly_warnings": validation["warnings"][
                "anomalies_over_200_percent_with_absolute_delta_over_1000"
            ],
        },
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
