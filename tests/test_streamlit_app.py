from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from etl import load_dati_comunali, load_provincia_belluno  # noqa: E402


def _format_integer(value: int, *, signed: bool = False) -> str:
    format_specifier = "+," if signed else ","
    return format(value, format_specifier).replace(",", ".")


def _expected_province_variation(metric: str) -> tuple[str, str, str]:
    provincia = load_provincia_belluno()
    years = sorted(int(year) for year in provincia["anno"].unique())[-2:]
    previous_year, recent_year = years
    recent_months = provincia.loc[
        provincia["anno"] == recent_year,
        "mese_num",
    ].unique()

    previous_value = int(
        provincia.loc[
            (provincia["anno"] == previous_year)
            & (provincia["mese_num"].isin(recent_months)),
            metric,
        ].sum()
    )
    recent_value = int(
        provincia.loc[
            (provincia["anno"] == recent_year)
            & (provincia["mese_num"].isin(recent_months)),
            metric,
        ].sum()
    )
    difference = recent_value - previous_value
    variation = difference / previous_value * 100
    label = (
        f"Variazione complessiva {metric.capitalize()} "
        f"{recent_year} vs {previous_year}"
    )
    return label, _format_integer(difference, signed=True), f"{variation:+.2f}%"


class StreamlitAppTests(unittest.TestCase):
    def test_dashboard_renders_comuni_provincia_and_stl_without_errors(self) -> None:
        test_password = "test-dashboard-password"
        os.environ["DASHBOARD_PASSWORD"] = test_password
        app = AppTest.from_file(REPOSITORY_ROOT / "app.py", default_timeout=30)
        app.run()
        self.assertFalse(app.exception)

        app.text_input[0].input(test_password).run()
        self.assertFalse(app.exception)

        comuni = load_dati_comunali()
        expected_comuni_years = sorted(
            int(year) for year in comuni["anno"].unique()
        )[-2:]
        comuni_years = next(
            multiselect
            for multiselect in app.sidebar.multiselect
            if multiselect.label == "Anno (Comuni)"
        )
        self.assertEqual(comuni_years.value, expected_comuni_years)

        ranking_titles = [markdown.value for markdown in app.markdown]
        for metric in ["Presenze", "Arrivi"]:
            self.assertIn(
                f"#### 📈 10 maggiori contributi alla crescita – {metric}",
                ranking_titles,
            )
            self.assertIn(
                f"#### 📉 10 maggiori contributi alla flessione – {metric}",
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
        provincia = load_provincia_belluno()
        expected_province_years = sorted(
            int(year) for year in provincia["anno"].unique()
        )[-2:]
        self.assertEqual(
            years_by_label["Anno (Provincia)"],
            expected_province_years,
        )
        self.assertEqual(years_by_label["Anno (STL)"], expected_province_years)

        headers = [header.value for header in app.header]
        self.assertIn("🏔️ Provincia di Belluno – Arrivi e Presenze mensili", headers)
        self.assertIn("🌄 STL Dolomiti – Arrivi e Presenze mensili", headers)

        metrics_by_label = {metric.label: metric for metric in app.metric}
        for metric_name in ("arrivi", "presenze"):
            label, expected_value, expected_delta = _expected_province_variation(
                metric_name
            )
            metric = metrics_by_label[label]
            self.assertEqual(metric.value, expected_value)
            self.assertEqual(metric.delta, expected_delta)


if __name__ == "__main__":
    unittest.main()
