"""Data access, validation, and calculations for the web dashboard.

The Streamlit UI depends only on this module's functions.  Keeping CSV access
behind this boundary makes it possible to add a PostgreSQL-backed repository
later without changing chart or page code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "consumption_monthly.csv"
DATA_PATH_ENV_VAR = "AEI_CONSUMPTION_DATA_PATH"
VIENNA_TIMEZONE = ZoneInfo("Europe/Vienna")

SOURCE_PROVIDER = "E-Control Austria"
SOURCE_SERIES_ID = "#89110m"
SOURCE_SERIES_NAME = "Inlandstromverbrauch"
SOURCE_REGION = "Austria"
SOURCE_FREQUENCY = "Monthly"
SOURCE_UNIT = "MWh"

REQUIRED_COLUMNS = frozenset({"month", "consumption_mwh"})
MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


class DataQualityError(ValueError):
    """Raised when dashboard input data is unsafe to analyse."""


@dataclass(frozen=True)
class DataQualitySummary:
    """Compact, user-facing quality and coverage metadata."""

    row_count: int
    start_month: pd.Timestamp
    end_month: pd.Timestamp
    complete_years: tuple[int, ...]
    latest_year: int
    latest_year_month_count: int

    @property
    def latest_year_is_complete(self) -> bool:
        return self.latest_year_month_count == 12


@dataclass(frozen=True)
class ConsumptionKpis:
    """Filter-responsive headline measures."""

    latest_month: pd.Timestamp
    latest_gwh: float
    latest_yoy_pct: float | None
    yoy_reference_month: pd.Timestamp | None
    average_monthly_gwh: float
    period_total_twh: float
    peak_month: pd.Timestamp
    peak_gwh: float
    month_count: int


@dataclass(frozen=True)
class SourceStatus:
    """Source identity and freshness information for the current dataset."""

    provider: str
    series_id: str
    series_name: str
    region: str
    frequency: str
    source_unit: str
    data_through: pd.Timestamp
    processed_file_updated: datetime
    row_count: int


def data_file_fingerprint(path: Path = DEFAULT_DATA_PATH) -> tuple[str, int, int]:
    """Return cache inputs that change whenever the processed CSV changes."""

    resolved = path.resolve()
    stat = resolved.stat()
    return str(resolved), stat.st_mtime_ns, stat.st_size


def configured_data_path() -> Path:
    """Return the configured consumption source path.

    The environment override supports deterministic tests and deployment data
    mounts while keeping the project's processed CSV as the local default.
    """

    configured = os.environ.get(DATA_PATH_ENV_VAR)
    return Path(configured) if configured else DEFAULT_DATA_PATH


def load_consumption_data(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load and validate the processed monthly consumption dataset."""

    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(
            f"Processed consumption data was not found at: {resolved}"
        )

    try:
        frame = pd.read_csv(resolved)
    except (
        OSError,
        UnicodeError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
    ) as exc:
        raise DataQualityError(f"Could not read processed consumption data: {exc}") from exc

    return prepare_consumption_data(frame)


def prepare_consumption_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate a monthly frame and add analysis-ready derived columns."""

    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise DataQualityError(f"Missing required column(s): {missing}")
    if frame.empty:
        raise DataQualityError("The processed consumption dataset is empty.")

    data = frame.loc[:, ["month", "consumption_mwh"]].copy()
    data["month"] = pd.to_datetime(
        data["month"], format="%Y-%m-%d", errors="coerce"
    )
    data["consumption_mwh"] = pd.to_numeric(
        data["consumption_mwh"], errors="coerce"
    )

    issues: list[str] = []
    if data["month"].isna().any():
        issues.append("month contains missing or invalid dates")
    if data["consumption_mwh"].isna().any():
        issues.append("consumption_mwh contains missing or non-numeric values")

    valid_months = data["month"].dropna()
    if not valid_months.empty and not valid_months.dt.is_month_start.all():
        issues.append("month values must be calendar month starts")
    if data["month"].duplicated().any():
        issues.append("duplicate months were detected")

    finite_values = data["consumption_mwh"].dropna().map(math.isfinite)
    if not finite_values.all():
        issues.append("consumption_mwh contains non-finite values")
    if (data["consumption_mwh"].dropna() <= 0).any():
        issues.append("consumption_mwh must contain only positive values")

    if issues:
        raise DataQualityError("; ".join(issues))

    data = data.sort_values("month").reset_index(drop=True)
    expected_months = pd.date_range(
        start=data["month"].min(), end=data["month"].max(), freq="MS"
    )
    actual_months = pd.DatetimeIndex(data["month"])
    missing_months = expected_months.difference(actual_months)
    if not missing_months.empty:
        labels = ", ".join(month.strftime("%Y-%m") for month in missing_months)
        raise DataQualityError(f"Missing monthly observations: {labels}")

    data["consumption_gwh"] = data["consumption_mwh"] / 1_000.0
    data["year"] = data["month"].dt.year.astype(int)
    data["month_number"] = data["month"].dt.month.astype(int)
    data["month_name"] = data["month_number"].map(MONTH_NAMES)
    data["monthly_yoy_pct"] = (
        data["consumption_gwh"].pct_change(periods=12, fill_method=None) * 100.0
    )
    data["yoy_reference_month"] = data["month"].shift(12).where(
        data["monthly_yoy_pct"].notna()
    )
    return data


def profile_consumption_data(data: pd.DataFrame) -> DataQualitySummary:
    """Summarize validated coverage and complete calendar years."""

    month_counts = data.groupby("year")["month_number"].nunique()
    complete_years = tuple(int(year) for year in month_counts[month_counts == 12].index)
    latest_year = int(data["year"].max())
    return DataQualitySummary(
        row_count=len(data),
        start_month=data["month"].min(),
        end_month=data["month"].max(),
        complete_years=complete_years,
        latest_year=latest_year,
        latest_year_month_count=int(month_counts.loc[latest_year]),
    )


def source_status(
    data: pd.DataFrame, path: Path = DEFAULT_DATA_PATH
) -> SourceStatus:
    """Build source and freshness metadata without treating file time as coverage."""

    return SourceStatus(
        provider=SOURCE_PROVIDER,
        series_id=SOURCE_SERIES_ID,
        series_name=SOURCE_SERIES_NAME,
        region=SOURCE_REGION,
        frequency=SOURCE_FREQUENCY,
        source_unit=SOURCE_UNIT,
        data_through=data["month"].max(),
        processed_file_updated=datetime.fromtimestamp(
            path.resolve().stat().st_mtime, tz=VIENNA_TIMEZONE
        ),
        row_count=len(data),
    )


def filter_consumption_data(
    data: pd.DataFrame, start_date: date | pd.Timestamp, end_date: date | pd.Timestamp
) -> pd.DataFrame:
    """Filter inclusively at monthly grain, normalizing inputs to month starts."""

    start_month = pd.Timestamp(start_date).to_period("M").to_timestamp()
    end_month = pd.Timestamp(end_date).to_period("M").to_timestamp()
    if start_month > end_month:
        raise ValueError("Start date must be on or before end date.")

    selected = data.loc[data["month"].between(start_month, end_month)].copy()
    return selected.reset_index(drop=True)


def calculate_kpis(
    selected: pd.DataFrame, full_history: pd.DataFrame
) -> ConsumptionKpis:
    """Calculate headline metrics for the visible rows.

    The latest-month YoY baseline intentionally comes from the validated full
    history so the comparison remains available when the prior year falls just
    outside the selected display range.
    """

    if selected.empty:
        raise ValueError("At least one monthly observation is required.")

    latest = selected.iloc[-1]
    previous_month = latest["month"] - pd.DateOffset(years=1)
    prior_match = full_history.loc[full_history["month"] == previous_month]

    latest_yoy_pct: float | None = None
    reference_month: pd.Timestamp | None = None
    if not prior_match.empty:
        prior_gwh = float(prior_match.iloc[0]["consumption_gwh"])
        latest_yoy_pct = (float(latest["consumption_gwh"]) / prior_gwh - 1.0) * 100.0
        reference_month = prior_match.iloc[0]["month"]

    peak = selected.loc[selected["consumption_gwh"].idxmax()]
    return ConsumptionKpis(
        latest_month=latest["month"],
        latest_gwh=float(latest["consumption_gwh"]),
        latest_yoy_pct=latest_yoy_pct,
        yoy_reference_month=reference_month,
        average_monthly_gwh=float(selected["consumption_gwh"].mean()),
        period_total_twh=float(selected["consumption_gwh"].sum() / 1_000.0),
        peak_month=peak["month"],
        peak_gwh=float(peak["consumption_gwh"]),
        month_count=len(selected),
    )


def build_trend_data(selected: pd.DataFrame, rolling_window: int) -> pd.DataFrame:
    """Add a full-window simple moving average to visible monthly rows."""

    if rolling_window < 2:
        raise ValueError("Rolling window must be at least two months.")
    trend = selected.copy()
    trend["rolling_average_gwh"] = trend["consumption_gwh"].rolling(
        window=rolling_window, min_periods=rolling_window
    ).mean()
    return trend


def build_seasonal_summary(selected: pd.DataFrame) -> pd.DataFrame:
    """Aggregate visible observations by calendar month."""

    seasonal = (
        selected.groupby("month_number", as_index=False)
        .agg(
            average_gwh=("consumption_gwh", "mean"),
            minimum_gwh=("consumption_gwh", "min"),
            maximum_gwh=("consumption_gwh", "max"),
            observations=("consumption_gwh", "size"),
        )
        .sort_values("month_number")
    )
    seasonal["month_name"] = seasonal["month_number"].map(MONTH_NAMES)
    return seasonal


def build_annual_summary(selected: pd.DataFrame) -> pd.DataFrame:
    """Return annual totals and YoY growth for complete calendar years only."""

    annual = (
        selected.groupby("year", as_index=False)
        .agg(
            month_count=("month_number", "nunique"),
            consumption_gwh=("consumption_gwh", "sum"),
        )
        .sort_values("year")
    )
    annual = annual.loc[annual["month_count"] == 12].copy()
    annual["consumption_twh"] = annual["consumption_gwh"] / 1_000.0
    annual["yoy_pct"] = (
        annual["consumption_gwh"].pct_change(fill_method=None) * 100.0
    )
    return annual.reset_index(drop=True)


def build_detail_table(selected: pd.DataFrame, rolling_window: int) -> pd.DataFrame:
    """Create the filtered table used by both the UI and CSV export."""

    detail = build_trend_data(selected, rolling_window)
    return detail.loc[
        :,
        [
            "month",
            "consumption_mwh",
            "consumption_gwh",
            "monthly_yoy_pct",
            "yoy_reference_month",
            "rolling_average_gwh",
        ],
    ]


def export_detail_csv(detail: pd.DataFrame, rolling_window: int) -> bytes:
    """Serialize exactly the filtered detail rows with explicit derived labels."""

    export = detail.copy()
    export["month"] = export["month"].dt.strftime("%Y-%m-%d")
    export["yoy_reference_month"] = export["yoy_reference_month"].dt.strftime(
        "%Y-%m-%d"
    )
    export = export.rename(
        columns={
            "monthly_yoy_pct": "year_over_year_pct",
            "rolling_average_gwh": f"rolling_{rolling_window}_month_average_gwh",
        }
    )
    return export.to_csv(index=False).encode("utf-8")
