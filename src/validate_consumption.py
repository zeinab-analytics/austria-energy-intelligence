
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "processed" / "consumption_monthly.csv"

df = pd.read_csv(INPUT_FILE, parse_dates=["month"])

# Check missing values
missing_values = df.isna().sum()

# Check duplicate months
duplicate_months = df["month"].duplicated().sum()

# Check negative consumption
negative_values = (df["consumption_mwh"] < 0).sum()

# Check missing months
expected_months = pd.date_range(
    start=df["month"].min(),
    end=df["month"].max(),
    freq="MS"
)

missing_months = expected_months.difference(df["month"])

print("=== Electricity Consumption Data Quality Report ===")
print(f"Total records: {len(df)}")
print(f"Expected months: {len(expected_months)}")
print(f"Missing months: {len(missing_months)}")
print(f"Duplicate months: {duplicate_months}")
print(f"Negative values: {negative_values}")
print(f"Missing values:\n{missing_values.to_string()}")

if len(missing_months) > 0:
    print("\nMissing month list:")
    print(missing_months.strftime("%Y-%m").tolist())

if (
    len(missing_months) == 0
    and duplicate_months == 0
    and negative_values == 0
    and missing_values.sum() == 0
):
    print("\nDATA QUALITY STATUS: PASSED")
else:
    print("\nDATA QUALITY STATUS: FAILED")
    raise SystemExit(1)
