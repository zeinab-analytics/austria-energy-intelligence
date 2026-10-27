# Austria Energy Intelligence

An automated, AI-powered platform for analyzing Austria's electricity system and market.

## Project Overview

Austria Energy Intelligence is a hands-on Data Engineering, Business Intelligence, and AI project built on real electricity data from official European and Austrian sources.

The platform will eventually support:

- Electricity consumption and generation analysis
- Electricity market price analysis
- Electricity imports and exports
- Daily, weekly, monthly, and yearly comparisons
- Historical trends and seasonal patterns
- Anomaly detection
- Consumption and price forecasting
- Interactive Power BI dashboards
- AI-generated insights and daily analytical reports
- Automated notifications and alerts

## Technology Stack

| Area | Technology |
|---|---|
| Version control | Git + GitHub |
| Development | Windows 11 + VS Code |
| Server | Personal Debian 13 server, running 24/7 |
| Deployment | Docker + Docker Compose |
| Data processing | Python + Pandas |
| Database | PostgreSQL |
| Automation | n8n |
| Dashboards | Power BI |
| Forecasting | Python-based statistical or ML models |
| AI integration | Online LLM API |
| Notifications | Existing Telegram bot |

Only the tools needed for the current phase are installed (currently Python, Pandas, and Matplotlib).

## Data Sources

Official, publicly accessible datasets, in priority order:

1. E-Control Austria (current source: monthly domestic electricity consumption)
2. Austrian Power Grid (APG)
3. ENTSO-E Transparency Platform
4. SMARD
5. Eurostat

Each dataset is verified for source, licensing, coverage, granularity, units, timestamps, quality, and update frequency before use.

## Project Structure

```text
austria-energy-intelligence/
├── data/
│   ├── raw/
│   └── processed/
├── src/
├── reports/
├── README.md
├── requirements.txt
└── .gitignore
```

Raw and processed data files and generated reports are not stored in Git.

## Phase 1 — Consumption Analysis

Place the E-Control export at `data/raw/el_dataset_mn.csv`, then run:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src\extract_consumption.py
.\.venv\Scripts\python.exe src\validate_consumption.py
.\.venv\Scripts\python.exe src\analyze_consumption.py
.\.venv\Scripts\python.exe src\visualize_consumption.py
```

| Script | Purpose |
|---|---|
| `src/extract_consumption.py` | Extracts and cleans the monthly consumption series into `data/processed/` |
| `src/validate_consumption.py` | Checks missing values, duplicates, negatives, and month continuity |
| `src/analyze_consumption.py` | Writes the analytical report to `reports/` |
| `src/visualize_consumption.py` | Saves the first trend chart to `reports/` |

## Development Roadmap

1. GitHub setup and first consumption analysis
2. PostgreSQL and additional datasets (generation, prices, imports/exports)
3. n8n automation
4. Power BI dashboards and KPIs
5. Anomaly detection and forecasting
6. AI agent with evidence-based daily reports
7. Telegram integration (extend the existing `telegram-ai-bot` with GitHub support)
8. Production deployment on Debian 13 with Docker Compose

## Current Status

Phase 1 is in progress: consumption ETL, validation, analysis, and first chart are implemented.

## License

No license has been selected yet. All rights reserved.
