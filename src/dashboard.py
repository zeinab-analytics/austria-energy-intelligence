"""Permanent Streamlit web interface for Austria Energy Intelligence."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dashboard_charts import (
    annual_totals_figure,
    annual_yoy_figure,
    monthly_trend_figure,
    seasonal_profile_figure,
)
from src.dashboard_data import (
    DataQualityError,
    build_annual_summary,
    build_detail_table,
    build_seasonal_summary,
    build_trend_data,
    calculate_kpis,
    configured_data_path,
    data_file_fingerprint,
    export_detail_csv,
    filter_consumption_data,
    load_consumption_data,
    profile_consumption_data,
    source_status,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STYLE_FILE = PROJECT_ROOT / "assets" / "dashboard.css"

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}


@st.cache_data(show_spinner=False)
def _load_cached_consumption(
    path: str, modified_time_ns: int, file_size: int
) -> pd.DataFrame:
    """Load data with a fingerprint that invalidates after an ETL refresh."""

    # The fingerprint arguments are intentionally part of Streamlit's cache key.
    _ = (modified_time_ns, file_size)
    return load_consumption_data(Path(path))


def _get_consumption_data() -> pd.DataFrame:
    data_path = configured_data_path()
    path, modified_time_ns, file_size = data_file_fingerprint(data_path)
    return _load_cached_consumption(path, modified_time_ns, file_size)


def _apply_styles() -> None:
    if STYLE_FILE.is_file():
        st.markdown(
            f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def _render_platform_header() -> None:
    st.markdown(
        """
        <header class="aei-shell-header">
            <div class="aei-shell-mark" aria-hidden="true">AT</div>
            <div class="aei-shell-copy">
                <p class="aei-eyebrow">AUSTRIAN ELECTRICITY ANALYTICS</p>
                <h1>Austria Energy Intelligence</h1>
                <p class="aei-shell-subtitle">
                    A modular analytics workspace for official electricity data.
                </p>
            </div>
            <div class="aei-shell-badge">Consumption data available</div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def _render_page_heading(title: str, description: str) -> None:
    st.markdown(f"## {title}")
    st.caption(description)


def _render_source_strip(status) -> None:
    coverage = status.data_through.strftime("%B %Y")
    processed = status.processed_file_updated.strftime("%d %B %Y, %H:%M %Z")
    st.markdown(
        f"""
        <div class="aei-data-strip" role="note">
            <span><strong>Source</strong> {escape(status.provider)}</span>
            <span><strong>Series</strong> {escape(status.series_id)}</span>
            <span><strong>Coverage</strong> through {escape(coverage)}</span>
            <span><strong>Local refresh</strong> {escape(processed)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _load_or_explain() -> pd.DataFrame | None:
    try:
        return _get_consumption_data()
    except FileNotFoundError:
        st.error(
            "The processed consumption dataset is unavailable. Run the existing "
            "extraction pipeline before starting the dashboard."
        )
        st.code("python src/extract_consumption.py", language="powershell")
    except DataQualityError as exc:
        st.error(f"The processed dataset failed dashboard quality checks: {exc}")
    except OSError as exc:
        st.error(f"The processed dataset could not be accessed: {exc}")
    return None


def render_overview() -> None:
    """Platform landing page with factual module and source status."""

    _render_page_heading(
        "Platform overview",
        "One interface for Austria's electricity system, market, forecasting, and AI analytics.",
    )
    data = _load_or_explain()
    if data is None:
        return

    quality = profile_consumption_data(data)
    status = source_status(data, configured_data_path())
    _render_source_strip(status)

    columns = st.columns(3)
    with columns[0]:
        with st.container(border=True, key="kpi_overview_module"):
            st.metric("Available analytics", "Consumption")
            st.caption("National monthly electricity consumption is live.")
    with columns[1]:
        with st.container(border=True, key="kpi_overview_coverage"):
            st.metric(
                "Validated coverage",
                f"{quality.row_count} months",
                f"{quality.start_month:%b %Y} – {quality.end_month:%b %Y}",
                delta_color="off",
            )
    with columns[2]:
        with st.container(border=True, key="kpi_overview_quality"):
            st.metric("Data quality", "Passed")
            st.caption("Continuous months, unique dates, positive numeric values.")

    st.markdown("### Platform modules")
    st.markdown(
        """
        <div class="aei-module-grid">
            <article class="aei-module-card aei-module-card--active">
                <span class="aei-module-status">AVAILABLE</span>
                <h3>Electricity Consumption</h3>
                <p>Interactive trends, seasonality, annual comparisons, growth, and exports.</p>
            </article>
            <article class="aei-module-card"><span class="aei-module-status">COMING SOON</span><h3>Electricity Generation</h3><p>Awaiting a validated official dataset.</p></article>
            <article class="aei-module-card"><span class="aei-module-status">COMING SOON</span><h3>Market Prices</h3><p>Awaiting a validated official dataset.</p></article>
            <article class="aei-module-card"><span class="aei-module-status">COMING SOON</span><h3>Imports &amp; Exports</h3><p>Awaiting a validated official dataset.</p></article>
            <article class="aei-module-card"><span class="aei-module-status">COMING SOON</span><h3>Forecasting</h3><p>No forecasting model has been implemented.</p></article>
            <article class="aei-module-card"><span class="aei-module-status">COMING SOON</span><h3>AI Insights</h3><p>No generated insights are shown without a validated analytical workflow.</p></article>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpis(selected: pd.DataFrame, full_history: pd.DataFrame) -> None:
    kpis = calculate_kpis(selected, full_history)
    yoy_delta = "YoY unavailable"
    if kpis.latest_yoy_pct is not None and kpis.yoy_reference_month is not None:
        yoy_delta = (
            f"{kpis.latest_yoy_pct:+.2f}% vs "
            f"{kpis.yoy_reference_month.strftime('%b %Y')}"
        )

    columns = st.columns(4)
    with columns[0]:
        with st.container(border=True, key="kpi_latest"):
            st.metric(
                f"Latest month · {kpis.latest_month:%b %Y}",
                f"{kpis.latest_gwh:,.1f} GWh",
                yoy_delta,
                delta_color="off",
                help=(
                    "Latest visible monthly consumption. The comparison uses the "
                    "same calendar month one year earlier from full history."
                ),
            )
    with columns[1]:
        with st.container(border=True, key="kpi_average"):
            st.metric("Monthly average", f"{kpis.average_monthly_gwh:,.1f} GWh")
            st.caption(f"Across {kpis.month_count} selected month(s)")
    with columns[2]:
        with st.container(border=True, key="kpi_total"):
            st.metric("Selected-period total", f"{kpis.period_total_twh:,.2f} TWh")
            st.caption("Sum of all visible monthly observations")
    with columns[3]:
        with st.container(border=True, key="kpi_peak"):
            st.metric(
                "Peak month",
                f"{kpis.peak_gwh:,.1f} GWh",
                kpis.peak_month.strftime("%b %Y"),
                delta_color="off",
            )


def render_consumption() -> None:
    """Complete interactive consumption analytics workspace."""

    _render_page_heading(
        "Electricity consumption",
        "Austria-wide monthly inland electricity consumption from E-Control.",
    )
    full_history = _load_or_explain()
    if full_history is None:
        return

    status = source_status(full_history, configured_data_path())
    quality = profile_consumption_data(full_history)
    _render_source_strip(status)

    with st.container(border=True, key="card_filters"):
        st.markdown("#### Analysis controls")
        filter_columns = st.columns([2.2, 1.0, 1.0])
        with filter_columns[0]:
            selected_dates = st.date_input(
                "Date range",
                value=(quality.start_month.date(), quality.end_month.date()),
                min_value=quality.start_month.date(),
                max_value=quality.end_month.date(),
                key="consumption_date_range",
                help="Dates are normalized to whole calendar months.",
            )
        with filter_columns[1]:
            rolling_window = st.selectbox(
                "Rolling average",
                options=(3, 6, 12),
                index=2,
                format_func=lambda months: f"{months} months",
                key="consumption_rolling_window",
            )
        with filter_columns[2]:
            st.metric("Data grain", "Monthly")
            st.caption("National total · Austria")

    if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
        st.info("Choose both a start and end date to display the analytics.")
        return

    selected = filter_consumption_data(
        full_history, selected_dates[0], selected_dates[1]
    )
    if selected.empty:
        st.warning("The selected date range contains no monthly observations.")
        return

    st.caption(
        f"Active view: {selected['month'].min():%B %Y} to "
        f"{selected['month'].max():%B %Y} · {len(selected)} monthly observations"
    )
    _render_kpis(selected, full_history)

    trend = build_trend_data(selected, int(rolling_window))
    with st.container(border=True, key="card_trend"):
        st.plotly_chart(
            monthly_trend_figure(trend, int(rolling_window)),
            width="stretch",
            height=450,
            theme=None,
            key="consumption_monthly_trend",
            config=PLOTLY_CONFIG,
            alt=(
                "Line chart of Austria's monthly electricity consumption and the "
                f"selected {rolling_window}-month rolling average."
            ),
        )
        if trend["rolling_average_gwh"].notna().sum() == 0:
            st.caption(
                f"A {rolling_window}-month rolling average needs at least "
                f"{rolling_window} selected observations."
            )
        else:
            st.caption(
                "Rolling values require a complete window and are calculated only "
                "from months inside the active date range."
            )

    seasonal = build_seasonal_summary(selected)
    with st.container(border=True, key="card_seasonal"):
        st.plotly_chart(
            seasonal_profile_figure(seasonal),
            width="stretch",
            height=400,
            theme=None,
            key="consumption_seasonal_profile",
            config=PLOTLY_CONFIG,
            alt=(
                "Seasonal profile showing average Austria electricity consumption "
                "for each calendar month in the selected range."
            ),
        )
        st.caption(
            "Averages use every selected observation for each calendar month; "
            "hover details show sample count and observed range. The y-axis is "
            "focused on the selected monthly averages to make seasonality readable."
        )

    st.markdown("### Annual comparison")
    st.caption(
        "Only calendar years with all 12 months inside the active range are included. "
        "Partial years are excluded from totals and growth calculations."
    )
    annual = build_annual_summary(selected)
    annual_columns = st.columns(2)
    with annual_columns[0]:
        with st.container(border=True, key="card_annual_totals"):
            if annual.empty:
                st.info("No complete calendar year is available in this date range.")
            else:
                st.plotly_chart(
                    annual_totals_figure(annual),
                    width="stretch",
                    height=410,
                    theme=None,
                    key="consumption_annual_totals",
                    config=PLOTLY_CONFIG,
                    alt="Bar chart of annual electricity consumption for complete years.",
                )
    with annual_columns[1]:
        with st.container(border=True, key="card_annual_yoy"):
            if len(annual) < 2:
                st.info(
                    "At least two complete calendar years are needed for annual growth."
                )
            else:
                st.plotly_chart(
                    annual_yoy_figure(annual),
                    width="stretch",
                    height=410,
                    theme=None,
                    key="consumption_annual_yoy",
                    config=PLOTLY_CONFIG,
                    alt=(
                        "Bar chart of year-over-year percentage change in annual "
                        "electricity consumption for complete years."
                    ),
                )

    st.markdown("### Monthly data")
    detail = build_detail_table(selected, int(rolling_window))
    display_detail = detail.rename(
        columns={
            "month": "Month",
            "consumption_mwh": "Consumption (MWh)",
            "consumption_gwh": "Consumption (GWh)",
            "monthly_yoy_pct": "YoY change (%)",
            "yoy_reference_month": "YoY reference month",
            "rolling_average_gwh": f"{rolling_window}-month average (GWh)",
        }
    )
    st.caption(
        "Monthly YoY values compare with the same calendar month in validated full "
        "history; the reference month can fall outside the active date range."
    )
    table_column, download_column = st.columns([4.2, 1.0])
    with table_column:
        with st.container(border=True, key="card_data_table"):
            st.dataframe(
                display_detail,
                width="stretch",
                height=390,
                hide_index=True,
                column_config={
                    "Month": st.column_config.DateColumn("Month", format="MMM YYYY"),
                    "Consumption (MWh)": st.column_config.NumberColumn(format="%.3f"),
                    "Consumption (GWh)": st.column_config.NumberColumn(format="%.2f"),
                    "YoY change (%)": st.column_config.NumberColumn(
                        format="%+.2f%%",
                        help="Same calendar month one year earlier in full history.",
                    ),
                    "YoY reference month": st.column_config.DateColumn(
                        "YoY reference month", format="MMM YYYY"
                    ),
                    f"{rolling_window}-month average (GWh)": st.column_config.NumberColumn(
                        format="%.2f"
                    ),
                },
            )
    with download_column:
        with st.container(border=True, key="card_download"):
            st.markdown("#### Export")
            st.caption("Downloads exactly the active monthly selection and derived fields.")
            filename = (
                "austria_consumption_"
                f"{selected['month'].min():%Y%m}_{selected['month'].max():%Y%m}.csv"
            )
            st.download_button(
                "Download CSV",
                data=export_detail_csv(detail, int(rolling_window)),
                file_name=filename,
                mime="text/csv",
                icon=":material/download:",
                on_click="ignore",
                width="stretch",
                key="download_consumption_csv",
            )

    with st.expander("Source, freshness, and calculation notes"):
        st.markdown(
            f"""
            - **Provider:** {status.provider}
            - **Series:** `{status.series_id}` — {status.series_name}
            - **Scope:** {status.region}, {status.frequency.lower()}, source unit {status.source_unit}
            - **Validated coverage:** {quality.start_month:%B %Y} to {quality.end_month:%B %Y}
            - **Latest year:** {quality.latest_year_month_count} month(s) available in {quality.latest_year}
            - **Quality checks:** required schema, valid month-start dates, monthly continuity,
              unique months, finite numeric values, and positive consumption
            - **Conversions:** GWh = MWh ÷ 1,000; TWh = GWh ÷ 1,000
            - **Monthly YoY:** same calendar month one year earlier in validated full history
            - **Annual YoY:** complete calendar years only
            """
        )


def _render_coming_soon(title: str, description: str) -> None:
    _render_page_heading(title, description)
    st.markdown(
        f"""
        <section class="aei-coming-soon">
            <span>COMING SOON</span>
            <h2>{escape(title)}</h2>
            <p>
                No validated dataset is connected to this section. It is intentionally
                empty until an official source, quality rules, and metric definitions
                are implemented.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_generation() -> None:
    _render_coming_soon(
        "Electricity generation",
        "Future generation mix, output, and capacity analytics.",
    )


def render_market_prices() -> None:
    _render_coming_soon(
        "Market prices",
        "Future wholesale price and market movement analytics.",
    )


def render_imports_exports() -> None:
    _render_coming_soon(
        "Imports & exports",
        "Future cross-border electricity flow analytics.",
    )


def render_forecasting() -> None:
    _render_coming_soon(
        "Forecasting",
        "Future validated demand and market forecasting workflows.",
    )


def render_ai_insights() -> None:
    _render_coming_soon(
        "AI insights",
        "Future evidence-linked analytical narratives and alerts.",
    )


def main() -> None:
    """Configure and run the permanent multipage application shell."""

    st.set_page_config(
        page_title="Austria Energy Intelligence",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_styles()
    _render_platform_header()

    pages = [
        st.Page(
            render_overview,
            title="Overview",
            icon=":material/dashboard:",
            url_path="overview",
        ),
        st.Page(
            render_consumption,
            title="Electricity Consumption",
            icon=":material/electric_bolt:",
            default=True,
        ),
        st.Page(
            render_generation,
            title="Electricity Generation",
            icon=":material/factory:",
            url_path="generation",
        ),
        st.Page(
            render_market_prices,
            title="Market Prices",
            icon=":material/euro:",
            url_path="market-prices",
        ),
        st.Page(
            render_imports_exports,
            title="Imports & Exports",
            icon=":material/swap_horiz:",
            url_path="imports-exports",
        ),
        st.Page(
            render_forecasting,
            title="Forecasting",
            icon=":material/query_stats:",
            url_path="forecasting",
        ),
        st.Page(
            render_ai_insights,
            title="AI Insights",
            icon=":material/auto_awesome:",
            url_path="ai-insights",
        ),
    ]
    selected_page = st.navigation(pages, position="top")
    selected_page.run()
