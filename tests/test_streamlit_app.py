from __future__ import annotations

import os
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class StreamlitAppTests(unittest.TestCase):
    def test_dashboard_renders_comuni_provincia_and_stl_without_errors(self) -> None:
        test_password = "test-dashboard-password"
        os.environ["DASHBOARD_PASSWORD"] = test_password
        app = AppTest.from_file(REPOSITORY_ROOT / "app.py", default_timeout=30)
        app.run()
        self.assertFalse(app.exception)

        app.text_input[0].input(test_password).run()
        self.assertFalse(app.exception)

        comuni_years = next(
            multiselect
            for multiselect in app.sidebar.multiselect
            if multiselect.label == "Anno (Comuni)"
        )
        self.assertEqual(comuni_years.value, [2025, 2026])

        ranking_titles = [markdown.value for markdown in app.markdown]
        for metric in ["Presenze", "Arrivi"]:
            self.assertIn(
                f"#### 📈 10 Comuni con crescita maggiore – {metric}",
                ranking_titles,
            )
            self.assertIn(
                f"#### 📉 10 Comuni con performance peggiore – {metric}",
                ranking_titles,
            )

        sidebar_labels = [checkbox.label for checkbox in app.sidebar.checkbox]
        self.assertIn("📍 Mostra dati Provincia di Belluno", sidebar_labels)
        self.assertIn("📍 Mostra dati STL", sidebar_labels)

        app.sidebar.checkbox[0].check()
        app.sidebar.checkbox[1].check()
        app.run()

        self.assertFalse(app.exception)
        years_by_label = {
            multiselect.label: multiselect.value
            for multiselect in app.sidebar.multiselect
        }
        self.assertEqual(years_by_label["Anno (Provincia)"], [2025, 2026])
        self.assertEqual(years_by_label["Anno (STL)"], [2025, 2026])

        headers = [header.value for header in app.header]
        self.assertIn("🏔️ Provincia di Belluno – Arrivi e Presenze mensili", headers)
        self.assertIn("🌄 STL Dolomiti – Arrivi e Presenze mensili", headers)

        metrics_by_label = {metric.label: metric for metric in app.metric}
        arrivi = metrics_by_label["Variazione complessiva Arrivi 2026 vs 2025"]
        presenze = metrics_by_label["Variazione complessiva Presenze 2026 vs 2025"]
        self.assertEqual(arrivi.value, "+27.849")
        self.assertEqual(arrivi.delta, "+3.71%")
        self.assertEqual(presenze.value, "+67.756")
        self.assertEqual(presenze.delta, "+2.65%")


if __name__ == "__main__":
    unittest.main()
