from __future__ import annotations

import unittest

import pandas as pd

from comuni_ranking import build_comuni_ranking


class ComuniRankingTests(unittest.TestCase):
    def setUp(self) -> None:
        rows = []
        values = {
            2025: {
                "Alfa": [100, 100, 900],
                "Beta": [200, 200, 900],
                "Gamma": [100, 100, 900],
                "Solo nuovo": [100, 100, 900],
            },
            2026: {
                "Alfa": [150, 200],
                "Beta": [100, 100],
                "Gamma": [100, 100],
                "Solo nuovo": [300, 300],
            },
        }
        for year, municipalities in values.items():
            for municipality, monthly_values in municipalities.items():
                for month_number, presences in enumerate(monthly_values, start=1):
                    if year == 2025 and municipality == "Solo nuovo":
                        continue
                    rows.append(
                        {
                            "anno": year,
                            "mese_num": month_number,
                            "mese": ["Gen", "Feb", "Mar"][month_number - 1],
                            "comune": municipality,
                            "presenze": presences,
                        }
                    )
        self.data = pd.DataFrame(rows)

    def test_partial_year_uses_only_available_months_in_both_years(self) -> None:
        result = build_comuni_ranking(self.data, 2026)

        self.assertEqual(result.months, ["Gen", "Feb"])
        self.assertEqual(result.eligible_municipalities, 3)
        self.assertEqual(result.excluded_municipalities, 1)

        alfa = result.data[result.data["comune"].eq("Alfa")].iloc[0]
        self.assertEqual(alfa["previous_value"], 200)
        self.assertEqual(alfa["current_value"], 350)
        self.assertAlmostEqual(alfa["variation_pct"], 75.0)
        self.assertEqual(result.data.iloc[0]["comune"], "Alfa")
        self.assertEqual(result.data.iloc[-1]["comune"], "Beta")

    def test_selected_months_are_respected(self) -> None:
        result = build_comuni_ranking(self.data, 2026, ["Feb"])

        self.assertEqual(result.months, ["Feb"])
        alfa = result.data[result.data["comune"].eq("Alfa")].iloc[0]
        self.assertEqual(alfa["previous_value"], 100)
        self.assertEqual(alfa["current_value"], 200)

    def test_missing_comparison_year_returns_empty_ranking(self) -> None:
        result = build_comuni_ranking(self.data, 2025)

        self.assertTrue(result.data.empty)
        self.assertEqual(result.comparison_year, 2024)


if __name__ == "__main__":
    unittest.main()
