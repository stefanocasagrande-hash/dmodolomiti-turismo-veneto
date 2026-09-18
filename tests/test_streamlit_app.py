from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class StreamlitAppTests(unittest.TestCase):
    def test_dashboard_renders_comuni_provincia_and_stl_without_errors(self) -> None:
        app = AppTest.from_file(REPOSITORY_ROOT / "app.py", default_timeout=30)
        app.run()
        self.assertFalse(app.exception)

        app.text_input[0].input("dolomiti").run()
        self.assertFalse(app.exception)

        sidebar_labels = [checkbox.label for checkbox in app.sidebar.checkbox]
        self.assertIn("📍 Mostra dati Provincia di Belluno", sidebar_labels)
        self.assertIn("📍 Mostra dati STL", sidebar_labels)

        app.sidebar.checkbox[0].check()
        app.sidebar.checkbox[1].check()
        app.run()

        self.assertFalse(app.exception)
        headers = [header.value for header in app.header]
        self.assertIn("🏔️ Provincia di Belluno – Arrivi e Presenze mensili", headers)
        self.assertIn("🌄 STL Dolomiti – Arrivi e Presenze mensili", headers)


if __name__ == "__main__":
    unittest.main()
