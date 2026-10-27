
# Austria Energy Intelligence

An automated, AI-powered data analytics platform for Austria's electricity system and market.

## Project Overview

Austria Energy Intelligence is a hands-on Data Engineering, Business Intelligence, and AI project built using real electricity data from official European and Austrian sources.

The project aims to collect, validate, process, analyze, and visualize electricity data and eventually generate automated analytical insights.

## Project Objectives

- Analyze electricity consumption and generation in Austria.
- Explore electricity market prices.
- Analyze electricity imports and exports.
- Identify historical trends and seasonal patterns.
- Detect anomalies in electricity data.
- Forecast electricity consumption and prices.
- Build a professional interactive web platform with Streamlit and Plotly.
- Generate AI-powered analytical reports.
- Deliver automated notifications through Telegram.

## Technology Stack

| Area | Technology |
|---|---|
| Version Control | Git & GitHub |
| Development | Python, Pandas, VS Code |
| Database | PostgreSQL |
| Automation | n8n |
| Web Interface | Streamlit |
| Visualization | Plotly, Matplotlib |
| AI Integration | Online LLM API |
| Notifications | Telegram |
| Deployment | Docker, Docker Compose, Debian 13 |

## Data Sources

Current and planned official data sources include:

- E-Control Austria (current electricity consumption source)
- Austrian Power Grid (APG)
- ENTSO-E Transparency Platform
- SMARD
- Eurostat

Data sources will be evaluated for licensing, coverage, quality, granularity, and update frequency before integration.

## Project Structure

```text
austria-energy-intelligence/
├── .streamlit/
│   └── config.toml
├── assets/
│   └── dashboard.css
├── data/
│   ├── raw/
│   └── processed/
├── app.py
├── src/
│   ├── dashboard.py
│   ├── dashboard_charts.py
│   ├── dashboard_data.py
│   └── ...
├── tests/
├── reports/
├── README.md
├── requirements.txt
└── .gitignore
```

## Web Dashboard

The Streamlit application is the main interface for the platform. It currently
implements real electricity consumption analytics and provides permanent
navigation for future generation, market price, cross-border flow, forecasting,
and AI insight modules. Future sections remain clearly marked as coming soon
until validated source data is integrated.

### Features

- Filter-responsive KPI cards
- Monthly consumption and rolling-average trends
- Calendar-month seasonal analysis
- Complete-year totals and year-over-year growth
- Interactive Plotly hover, pan, and zoom controls
- Filtered monthly data table and CSV export
- Visible E-Control source, coverage, and calculation notes
- Runtime checks for schema, date continuity, uniqueness, and positive values

### Install and launch

For a first-time Windows setup, create the Python 3.14 virtual environment from
the repository root, install the declared versions, and launch the app:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The application opens in the default browser. If the processed dataset is not
available, place the E-Control source export at
`data/raw/el_dataset_mn.csv`, then create and validate the processed file with
the existing ETL scripts. Raw and processed data files are intentionally not
stored in Git.

```powershell
.\.venv\Scripts\python.exe src\extract_consumption.py
.\.venv\Scripts\python.exe src\validate_consumption.py
```

The dashboard reads `data/processed/consumption_monthly.csv`. Data access and
all calculations are isolated from the Plotly figure builders. A future
PostgreSQL adapter can replace the `_get_consumption_data` boundary while the
analytical page and chart contracts remain unchanged.

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Development Roadmap

1. GitHub setup and initial electricity consumption analysis
2. PostgreSQL integration and additional datasets
3. Automated data pipelines with n8n
4. Expand the Streamlit platform across additional electricity datasets
5. Anomaly detection and forecasting
6. AI-powered analytical insights
7. Telegram integration
8. Production deployment on Debian 13

## Current Status

Phase 1 consumption ETL and the permanent Streamlit web interface are implemented.
Additional platform modules remain on the roadmap.

## License

No license has been selected yet. All rights reserved.
