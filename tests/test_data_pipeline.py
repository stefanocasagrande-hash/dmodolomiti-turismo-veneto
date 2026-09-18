from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from normalize_turismo import normalize_official_data  # noqa: E402
from validate_turismo import ValidationError, validate_data  # noqa: E402


MOVEMENT_HEADER = (
    "progressivo;anno;ambito territoriale;dettaglio;Mese;Arrivi italiani;"
    "Arrivi stranieri;Presenze italiani;Presenze stranieri;Totale arrivi;"
    "Totale presenze\n"
)


def movement_csv(year: int, scope: str, detail: str, factor: int) -> str:
    rows = []
    months = ["Gennaio", "Febbraio", "Marzo"]
    for number, month in enumerate(months, start=1):
        ai, ae = factor * number, factor * number * 2
        pi, pe = factor * number * 3, factor * number * 4
        rows.append(
            f"{number};{year}, periodo Gennaio-Febbraio;{scope};{detail};{month};"
            f"{ai};{ae};{pi};{pe};{ai + ae};{pi + pe}\n"
        )
    return MOVEMENT_HEADER + "".join(rows)


def commune_csv(year: int, metric: str) -> str:
    title = metric.capitalize()
    columns = ";".join(f'"{month} {title}"' for month in [
        "Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"
    ])
    values = ";".join(["10", "20"] + ["0"] * 10)
    return (
        f'progressivo;anno;provenienza;"Comuni";{columns};"Totale {metric}"\n'
        f"1;{year};Italiani + stranieri;25001 - Agordo;{values};30\n"
    )


class PipelineTests(unittest.TestCase):
    def test_future_zero_months_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_root = Path(directory) / "raw"
            year_dir = raw_root / "2026"
            year_dir.mkdir(parents=True)
            files = {
                "provincia_belluno.csv": movement_csv(2026, "PROVINCIA", "Belluno", 3),
                "stl_dolomiti.csv": movement_csv(2026, "STL", "01 Dolomiti", 2),
                "stl_belluno.csv": movement_csv(2026, "STL", "02 Belluno", 1),
                "comuni_veneto_arrivi.csv": commune_csv(2026, "arrivi"),
                "comuni_veneto_presenze.csv": commune_csv(2026, "presenze"),
            }
            manifest_files = {}
            for name, content in files.items():
                path = year_dir / name
                path.write_text(content, encoding="utf-8")
                relative = path.relative_to(raw_root).as_posix()
                manifest_files[relative] = {
                    "source_url": f"https://example.test/{name}",
                    "acquired_at_utc": "2026-09-18T00:00:00+00:00",
                    "sha256": "test",
                    "bytes": len(content),
                }
            (raw_root / "manifest.json").write_text(
                json.dumps({"files": manifest_files}), encoding="utf-8"
            )

            output = Path(directory) / "processed.csv"
            data = normalize_official_data(raw_root, output)

            self.assertEqual(set(data["mese_num"]), {1, 2})
            self.assertFalse((data["mese_num"] == 3).any())
            report = validate_data(data)
            self.assertEqual(report["latest_period"], {"year": 2026, "month": 2})

    def test_validation_rejects_duplicate_keys(self) -> None:
        row = {
            "anno": 2026,
            "mese_num": 1,
            "mese": "Gennaio",
            "ambito": "PROVINCIA",
            "territorio_codice": "BL",
            "territorio": "Belluno",
            "provenienza": "Totale",
            "arrivi": 1,
            "presenze": 2,
            "stato_dato": "provvisorio",
            "fonte_url": "https://example.test",
            "data_acquisizione_utc": "2026-09-18T00:00:00+00:00",
            "source_file": "test.csv",
        }
        with self.assertRaisesRegex(ValidationError, "duplicate"):
            validate_data(pd.DataFrame([row, row]))


if __name__ == "__main__":
    unittest.main()
