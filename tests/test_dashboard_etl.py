from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from etl import load_dati_comunali, load_provincia_belluno, load_stl_data  # noqa: E402


def _row(
    scope: str,
    code: str,
    territory: str,
    origin: str,
    month: int,
    arrivals: int,
    nights: int,
) -> dict[str, object]:
    return {
        "anno": 2026,
        "mese_num": month,
        "mese": "nome esteso non usato dalla dashboard",
        "ambito": scope,
        "territorio_codice": code,
        "territorio": territory,
        "provenienza": origin,
        "arrivi": arrivals,
        "presenze": nights,
        "stato_dato": "provvisorio",
        "fonte_url": "https://example.test",
        "data_acquisizione_utc": "2026-09-18T00:00:00+00:00",
        "source_file": "test.csv",
    }


class DashboardEtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.dataset = Path(self.temporary_directory.name) / "movimento_turistico.csv"
        rows = [
            _row("COMUNE", "25001", "Agordo", "Totale", 1, 10, 20),
            _row("COMUNE", "25001", "Agordo", "Totale", 2, 11, 21),
            _row("PROVINCIA", "BL", "Belluno", "Italiani", 1, 40, 80),
            _row("PROVINCIA", "BL", "Belluno", "Stranieri", 1, 60, 120),
            _row("PROVINCIA", "BL", "Belluno", "Totale", 1, 100, 200),
            _row("STL", "01", "Dolomiti", "Totale", 1, 70, 140),
            _row("STL", "02", "Belluno - Feltre - Alpago", "Totale", 1, 30, 60),
        ]
        pd.DataFrame(rows).to_csv(self.dataset, index=False)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_comuni_keep_only_published_months_and_use_dashboard_labels(self) -> None:
        data = load_dati_comunali(self.dataset)

        self.assertEqual(data["mese"].tolist(), ["Gen", "Feb"])
        self.assertEqual(data["comune"].tolist(), ["Agordo", "Agordo"])
        self.assertEqual(data["presenze"].tolist(), [20, 21])

    def test_province_uses_total_without_duplicating_origins(self) -> None:
        data = load_provincia_belluno(self.dataset)

        self.assertEqual(len(data), 1)
        self.assertEqual(int(data.iloc[0]["arrivi"]), 100)
        self.assertEqual(int(data.iloc[0]["presenze"]), 200)

    def test_stl_are_split_in_the_expected_dashboard_order(self) -> None:
        dolomiti, belluno = load_stl_data(self.dataset)

        self.assertEqual(int(dolomiti.iloc[0]["presenze"]), 140)
        self.assertEqual(int(belluno.iloc[0]["presenze"]), 60)

    def test_repository_dataset_is_compatible_with_dashboard(self) -> None:
        repository_dataset = REPOSITORY_ROOT / "data/processed/movimento_turistico.csv"
        comuni = load_dati_comunali(repository_dataset)
        provincia = load_provincia_belluno(repository_dataset)
        dolomiti, belluno = load_stl_data(repository_dataset)

        self.assertFalse(comuni.empty)
        self.assertFalse(provincia.empty)
        self.assertFalse(dolomiti.empty)
        self.assertFalse(belluno.empty)
        self.assertEqual(int(comuni["anno"].max()), 2026)
        self.assertEqual(
            int(comuni.loc[comuni["anno"] == 2026, "mese_num"].max()),
            7,
        )


if __name__ == "__main__":
    unittest.main()
