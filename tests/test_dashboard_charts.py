from __future__ import annotations

import unittest

import pandas as pd

from src.dashboard_charts import monthly_trend_figure, seasonal_profile_figure
from src.dashboard_data import build_seasonal_summary, build_trend_data, prepare_consumption_data


class DashboardChartTests(unittest.TestCase):
    def test_one_month_trend_has_a_visible_marker(self) -> None:
        prepared = prepare_consumption_data(
            pd.DataFrame(
                {"month": ["2025-01-01"], "consumption_mwh": [6_000_000]}
            )
        )
        trend = build_trend_data(prepared, rolling_window=3)
        figure = monthly_trend_figure(trend, rolling_window=3)

        self.assertIn("markers", figure.data[0].mode)
        self.assertEqual(len(figure.data[0].x), 1)

    def test_seasonal_axis_is_focused_but_contains_all_averages(self) -> None:
        prepared = prepare_consumption_data(
            pd.DataFrame(
                {
                    "month": pd.date_range("2024-01-01", periods=12, freq="MS"),
                    "consumption_mwh": [5_000_000 + month * 100_000 for month in range(12)],
                }
            )
        )
        seasonal = build_seasonal_summary(prepared)
        figure = seasonal_profile_figure(seasonal)
        lower, upper = figure.layout.yaxis.range

        self.assertLess(lower, seasonal["average_gwh"].min())
        self.assertGreater(upper, seasonal["average_gwh"].max())
        self.assertGreater(lower, 0)


if __name__ == "__main__":
    unittest.main()
