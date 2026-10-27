from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.dashboard_data import DATA_PATH_ENV_VAR, PROJECT_ROOT


FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "consumption_monthly.csv"


class DashboardSmokeTests(unittest.TestCase):
    def test_default_consumption_page_starts_without_exception(self) -> None:
        with patch.dict(os.environ, {DATA_PATH_ENV_VAR: str(FIXTURE_PATH)}):
            app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30)
            app.run()

        self.assertFalse(app.exception)
        self.assertEqual(
            app.date_input(key="consumption_date_range").label, "Date range"
        )
        self.assertEqual(
            app.selectbox(key="consumption_rolling_window").value, 12
        )
        self.assertGreaterEqual(len(app.metric), 5)
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(len(app.download_button), 1)
        self.assertEqual(len(app.get("plotly_chart")), 4)

    def test_date_filter_updates_table_to_selected_months(self) -> None:
        with patch.dict(os.environ, {DATA_PATH_ENV_VAR: str(FIXTURE_PATH)}):
            app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30)
            app.run()
            app.date_input(key="consumption_date_range").set_value(
                (date(2010, 1, 1), date(2010, 6, 1))
            ).run()

        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe[0].value), 6)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertIn("Selected-period total", metrics)

    def test_missing_data_path_renders_recovery_error(self) -> None:
        missing_path = Path(PROJECT_ROOT / "tests" / "fixtures" / "missing.csv")
        with patch.dict(os.environ, {DATA_PATH_ENV_VAR: str(missing_path)}):
            app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30)
            app.run()

        self.assertFalse(app.exception)
        self.assertEqual(len(app.error), 1)


if __name__ == "__main__":
    unittest.main()
