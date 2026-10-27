
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "consumption_monthly.csv"
OUTPUT_FILE = BASE_DIR / "reports" / "consumption_analysis.txt"

df = pd.read_csv(INPUT_FILE, parse_dates=["month"])
df = df.sort_values("month")

# Convert MWh to GWh
df["consumption_gwh"] = df["consumption_mwh"] / 1000

# Add time dimensions
df["year"] = df["month"].dt.year
df["month_number"] = df["month"].dt.month

# Calculate descriptive statistics
average = df["consumption_gwh"].mean()
minimum = df.loc[df["consumption_gwh"].idxmin()]
maximum = df.loc[df["consumption_gwh"].idxmax()]

# Monthly seasonal averages
monthly_average = df.groupby("month_number")["consumption_gwh"].mean()

# Annual totals - exclude incomplete years
year_counts = df.groupby("year")["month_number"].nunique()
complete_years = year_counts[year_counts == 12].index

annual_totals = (
    df[df["year"].isin(complete_years)]
    .groupby("year")["consumption_gwh"]
    .sum()
)

annual_yoy = annual_totals.pct_change() * 100

# Build report
lines = [
    "AUSTRIA ELECTRICITY CONSUMPTION ANALYSIS",
    "=" * 45,
    f"Records: {len(df)}",
    f"Period: {df['month'].min():%Y-%m} to {df['month'].max():%Y-%m}",
    f"Average monthly consumption: {average:,.2f} GWh",
    f"Minimum: {minimum['consumption_gwh']:,.2f} GWh ({minimum['month']:%Y-%m})",
    f"Maximum: {maximum['consumption_gwh']:,.2f} GWh ({maximum['month']:%Y-%m})",
    "",
    "MONTHLY SEASONAL AVERAGES (GWh)",
    monthly_average.round(2).to_string(),
    "",
    "ANNUAL TOTALS (GWh) - COMPLETE YEARS ONLY",
    annual_totals.round(2).to_string(),
    "",
    "ANNUAL YEAR-OVER-YEAR CHANGE (%)",
    annual_yoy.round(2).to_string(),
]

report = "\n".join(lines)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text(report, encoding="utf-8")

print(report)
print(f"\nReport saved to: {OUTPUT_FILE}")
