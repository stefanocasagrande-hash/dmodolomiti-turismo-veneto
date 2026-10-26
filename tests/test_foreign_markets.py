from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from fetch_mercati_esteri import (  # noqa: E402
    discover_markets,
    parse_monthly_series,
    validate_market_data,
)

spec = importlib.util.spec_from_file_location(
    "markets_etl", REPOSITORY_ROOT / "paesi-di-provenienza" / "etl.py"
)
markets_etl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(markets_etl)


def analytical_fixture() -> pd.DataFrame:
    rows = []
    values = {
        "2022/23": {"Polonia": 100, "Germania": 80, "Francia": 20},
        "2023/24": {"Polonia": 120, "Germania": 70, "Francia": 30},
        "2024/25": {"Polonia": 140, "Germania": 75, "Francia": 45},
    }
    for season, markets in values.items():
        start = int(season[:4])
        for month in [12, 1, 2, 3]:
            year = start if month == 12 else start + 1
            for market, total in markets.items():
                rows.append(
                    {
                        "anno": year,
                        "mese_num": month,
                        "mese": markets_etl.MONTHS[month - 1],
                        "territorio": "Provincia di Belluno (DMO)",
                        "mercato": market,
                        "mercato_tipo": "Paese",
                        "presenze": total // 4,
                    }
                )
            rows.append(
                {
                    "anno": year,
                    "mese_num": month,
                    "mese": markets_etl.MONTHS[month - 1],
                    "territorio": "Provincia di Belluno (DMO)",
                    "mercato": "Totale stranieri",
                    "mercato_tipo": "Totale estero",
                    "presenze": sum(markets.values()) // 4,
                }
            )
    return pd.DataFrame(rows)


class ForeignMarketFetchTests(unittest.TestCase):
    def test_discovers_only_foreign_market_selector(self) -> None:
        page = """
        <select name="territorio"><option value="01_Dolomiti">Dolomiti</option></select>
        <select name="stato">
          <option value="99_MONDO">MONDO</option>
          <option value="98_TOTALE ITALIANI">TOTALE ITALIANI</option>
          <option value="97_TOTALE STRANIERI">TOTALE STRANIERI</option>
          <option value="35_Polonia">Polonia</option>
          <option value="37_Gran Bretagna">Gran Bretagna</option>
        </select>
        """
        self.assertEqual(
            discover_markets(page),
            [
                ("97_TOTALE STRANIERI", "Totale stranieri"),
                ("35_Polonia", "Polonia"),
                ("37_Gran Bretagna", "Regno Unito"),
            ],
        )

    def test_parses_monthly_chart_values(self) -> None:
        page = """
        <area title="(2026, Gen) = 39.044" />
        <area title="(2026, Feb) = 41.253" />
        <area title="(2025, Dic) = 9.129" />
        """
        rows = parse_monthly_series(
            page,
            territory_code="STL_DOLOMITI",
            territory="STL Dolomiti",
            market_code="35_Polonia",
            market="Polonia",
            source_url="https://example.test",
            start_year=2025,
            current_year=2026,
        )
        self.assertEqual([row["presenze"] for row in rows], [9129, 39044, 41253])
        self.assertEqual(rows[-1]["stato_dato"], "provvisorio")


class ForeignMarketAnalysisTests(unittest.TestCase):
    def test_last_three_complete_winter_seasons(self) -> None:
        data = analytical_fixture()
        table, totals, seasons = markets_etl.winter_market_comparison(
            data, "Provincia di Belluno (DMO)", seasons_count=3, top_n=2
        )
        self.assertEqual(seasons, ["2022/23", "2023/24", "2024/25"])
        self.assertEqual(table.iloc[0]["mercato"], "Polonia")
        self.assertEqual(int(table.iloc[0]["2024/25"]), 140)
        self.assertEqual(int(totals["2024/25"]), 260)

    def test_validation_rejects_incoherent_total(self) -> None:
        rows = [
            {
                "anno": 2025, "mese_num": 1, "territorio_codice": "BL",
                "mercato_codice": "97", "mercato_tipo": "Totale estero", "presenze": 11,
            },
            {
                "anno": 2025, "mese_num": 1, "territorio_codice": "BL",
                "mercato_codice": "35", "mercato_tipo": "Paese", "presenze": 10,
            },
        ]
        with self.assertRaises(Exception):
            validate_market_data(pd.DataFrame(rows))

    def test_validation_rejects_an_incomplete_market_series(self) -> None:
        rows = [
            {
                "anno": 2025, "mese_num": month, "territorio_codice": "BL",
                "mercato_codice": "97", "mercato_tipo": "Totale estero", "presenze": 10,
            }
            for month in [1, 2]
        ]
        rows.append(
            {
                "anno": 2025, "mese_num": 1, "territorio_codice": "BL",
                "mercato_codice": "35", "mercato_tipo": "Paese", "presenze": 10,
            }
        )
        with self.assertRaises(Exception):
            validate_market_data(pd.DataFrame(rows))


class ForeignMarketDashboardTests(unittest.TestCase):
    def test_dashboard_renders_without_exceptions(self) -> None:
        app = AppTest.from_file(
            str(REPOSITORY_ROOT / "paesi-di-provenienza" / "app.py")
        )
        app.run(timeout=30)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.title[0].value, "Mercati esteri delle Dolomiti Bellunesi")
        self.assertEqual(len(app.tabs), 5)
        self.assertEqual(app.tabs[1].label, "Focus inverno")


if __name__ == "__main__":
    unittest.main()

