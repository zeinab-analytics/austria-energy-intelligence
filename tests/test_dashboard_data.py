from __future__ import annotations

import unittest

import pandas as pd

from src.dashboard_data import (
    DEFAULT_DATA_PATH,
    DataQualityError,
    build_annual_summary,
    build_detail_table,
    build_trend_data,
    calculate_kpis,
    export_detail_csv,
    filter_consumption_data,
    load_consumption_data,
    prepare_consumption_data,
    profile_consumption_data,
)


class ConsumptionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = pd.DataFrame(
            {
                "month": pd.date_range("2023-01-01", periods=24, freq="MS"),
                "consumption_mwh": [5_000_000 + index * 10_000 for index in range(24)],
            }
        )

    def test_prepare_adds_expected_derived_columns(self) -> None:
        prepared = prepare_consumption_data(self.fixture)

        self.assertEqual(len(prepared), 24)
        self.assertIn("consumption_gwh", prepared.columns)
        self.assertIn("monthly_yoy_pct", prepared.columns)
        self.assertAlmostEqual(prepared.loc[0, "consumption_gwh"], 5_000.0)
        self.assertTrue(pd.isna(prepared.loc[11, "monthly_yoy_pct"]))
        self.assertFalse(pd.isna(prepared.loc[12, "monthly_yoy_pct"]))
        self.assertAlmostEqual(
            prepared.loc[12, "monthly_yoy_pct"],
            (5_120_000 / 5_000_000 - 1) * 100,
        )

    def test_missing_month_is_rejected(self) -> None:
        with self.assertRaisesRegex(DataQualityError, "Missing monthly observations"):
            prepare_consumption_data(self.fixture.drop(index=5))

    def test_duplicate_month_is_rejected(self) -> None:
        duplicated = pd.concat([self.fixture, self.fixture.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(DataQualityError, "duplicate months"):
            prepare_consumption_data(duplicated)

    def test_non_positive_value_is_rejected(self) -> None:
        invalid = self.fixture.copy()
        invalid.loc[0, "consumption_mwh"] = 0

        with self.assertRaisesRegex(DataQualityError, "positive values"):
            prepare_consumption_data(invalid)

    def test_filter_and_export_preserve_active_rows(self) -> None:
        prepared = prepare_consumption_data(self.fixture)
        selected = filter_consumption_data(prepared, "2023-04-18", "2023-09-02")
        detail = build_detail_table(selected, rolling_window=3)
        exported = export_detail_csv(detail, rolling_window=3).decode("utf-8")

        self.assertEqual(len(selected), 6)
        self.assertEqual(selected.iloc[0]["month"], pd.Timestamp("2023-04-01"))
        self.assertEqual(selected.iloc[-1]["month"], pd.Timestamp("2023-09-01"))
        self.assertEqual(len(exported.strip().splitlines()), 7)
        self.assertIn("rolling_3_month_average_gwh", exported.splitlines()[0])
        self.assertIn("yoy_reference_month", exported.splitlines()[0])

    def test_filter_rejects_reversed_dates(self) -> None:
        prepared = prepare_consumption_data(self.fixture)

        with self.assertRaisesRegex(ValueError, "Start date"):
            filter_consumption_data(prepared, "2024-01-01", "2023-01-01")

    def test_rolling_average_requires_a_complete_window(self) -> None:
        prepared = prepare_consumption_data(self.fixture)
        trend = build_trend_data(prepared.iloc[:4], rolling_window=3)

        self.assertTrue(trend["rolling_average_gwh"].iloc[:2].isna().all())
        self.assertAlmostEqual(
            trend.loc[2, "rolling_average_gwh"],
            prepared.loc[:2, "consumption_gwh"].mean(),
        )

    def test_yoy_baseline_can_come_from_outside_visible_range(self) -> None:
        prepared = prepare_consumption_data(self.fixture)
        selected = filter_consumption_data(prepared, "2024-01-01", "2024-01-01")
        kpis = calculate_kpis(selected, prepared)
        detail = build_detail_table(selected, rolling_window=3)

        self.assertEqual(kpis.yoy_reference_month, pd.Timestamp("2023-01-01"))
        self.assertFalse(pd.isna(kpis.latest_yoy_pct))
        self.assertEqual(
            detail.iloc[0]["yoy_reference_month"], pd.Timestamp("2023-01-01")
        )
        self.assertTrue(pd.isna(detail.iloc[0]["rolling_average_gwh"]))


@unittest.skipUnless(DEFAULT_DATA_PATH.is_file(), "Local processed dataset unavailable")
class ActualConsumptionDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_consumption_data()
        cls.known_cutoff = cls.data.loc[
            cls.data["month"] <= pd.Timestamp("2026-08-01")
        ].copy()

    def test_actual_dataset_quality_and_coverage(self) -> None:
        live_profile = profile_consumption_data(self.data)
        known_profile = profile_consumption_data(self.known_cutoff)

        self.assertGreaterEqual(live_profile.row_count, 200)
        self.assertEqual(live_profile.start_month, pd.Timestamp("2010-01-01"))
        self.assertGreaterEqual(live_profile.end_month, pd.Timestamp("2026-08-01"))
        self.assertEqual(known_profile.row_count, 200)
        self.assertEqual(known_profile.end_month, pd.Timestamp("2026-08-01"))
        self.assertEqual(known_profile.latest_year_month_count, 8)
        self.assertFalse(known_profile.latest_year_is_complete)
        self.assertEqual(known_profile.complete_years, tuple(range(2010, 2026)))

    def test_full_history_kpis_reconcile(self) -> None:
        kpis = calculate_kpis(self.known_cutoff, self.known_cutoff)

        self.assertAlmostEqual(kpis.latest_gwh, 5_562.350051, places=6)
        self.assertEqual(round(kpis.latest_yoy_pct or 0, 2), 2.09)
        self.assertEqual(kpis.latest_month, pd.Timestamp("2026-08-01"))

    def test_latest_rolling_average_reconciles(self) -> None:
        trend = build_trend_data(self.known_cutoff, rolling_window=12)

        self.assertAlmostEqual(
            trend.iloc[-1]["rolling_average_gwh"], 6_074.358163, places=5
        )

    def test_annual_summary_excludes_partial_2026(self) -> None:
        annual = build_annual_summary(self.known_cutoff)
        total_2025 = annual.loc[annual["year"] == 2025, "consumption_gwh"].iloc[0]
        yoy_2025 = annual.loc[annual["year"] == 2025, "yoy_pct"].iloc[0]

        self.assertEqual(annual["year"].tolist(), list(range(2010, 2026)))
        self.assertNotIn(2026, annual["year"].tolist())
        self.assertAlmostEqual(total_2025, 71_515.83, places=2)
        self.assertEqual(round(yoy_2025, 2), 2.26)


if __name__ == "__main__":
    unittest.main()
