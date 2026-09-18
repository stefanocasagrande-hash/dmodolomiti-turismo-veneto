from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd


class AppCompatibilityTests(unittest.TestCase):
    def test_apps_do_not_use_removed_styler_applymap(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        for relative_path in ["app.py", "paesi-di-provenienza/app.py"]:
            source = (repository_root / relative_path).read_text(encoding="utf-8")
            self.assertNotIn(".applymap(", source, relative_path)

    def test_tables_use_current_pandas_styler_api(self) -> None:
        table = pd.DataFrame(
            {
                "Presenze": [100, 110],
                "Variazione %": [pd.NA, 10.0],
            }
        )

        styled = table.style.map(
            lambda value: "color: green;" if pd.notna(value) and value > 0 else "",
            subset=["Variazione %"],
        )

        self.assertIn("color: green", styled.to_html())


if __name__ == "__main__":
    unittest.main()
