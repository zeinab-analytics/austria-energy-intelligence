
from pathlib import Path
import pandas as pd

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "raw" / "el_dataset_mn.csv"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "consumption_monthly.csv"

TARGET_SERIES = "#89110m"

# Read the original E-Control dataset
df = pd.read_csv(
    INPUT_FILE,
    sep=";",
    encoding="cp1252",
    dtype=str
)

# Find the target time series in the metadata
series_row = df.loc[df["Header & Timestamp"] == "TS_ID"]

if series_row.empty:
    raise ValueError("TS_ID metadata row not found")

matching_columns = [
    col for col in df.columns[1:]
    if series_row.iloc[0][col] == TARGET_SERIES
]

if len(matching_columns) != 1:
    raise ValueError(
        f"Expected one matching series, found {len(matching_columns)}"
    )

series_column = matching_columns[0]

# Verify source metadata
expected_metadata = {
    "KOMP": "Inlandstromverbrauch",
    "REG": "AT",
    "ZA": "mn",
    "UNIT": "MWh",
}

for field, expected in expected_metadata.items():
    actual = df.loc[
        df["Header & Timestamp"] == field,
        series_column
    ].iloc[0]

    if actual != expected:
        raise ValueError(
            f"Invalid {field}: expected {expected}, got {actual}"
        )

# Extract monthly observations
data = df[
    df["Header & Timestamp"].str.fullmatch(r"\d{4}-\d{2}", na=False)
][["Header & Timestamp", series_column]].copy()

data.columns = ["month", "consumption_mwh"]

# Convert data types
data["month"] = pd.to_datetime(
    data["month"], format="%Y-%m", errors="raise"
)

data["consumption_mwh"] = pd.to_numeric(
    data["consumption_mwh"].str.replace(",", ".", regex=False),
    errors="raise"
)

# Data quality checks
assert not data.isna().any().any(), "Missing values detected"
assert data["month"].is_unique, "Duplicate months detected"
assert (data["consumption_mwh"] >= 0).all(), "Negative consumption detected"

data = data.sort_values("month").reset_index(drop=True)

# Export processed dataset
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
data.to_csv(OUTPUT_FILE, index=False)

print("Extraction completed successfully!")
print(f"Records: {len(data)}")
print(f"First month: {data['month'].min():%Y-%m}")
print(f"Last month: {data['month'].max():%Y-%m}")
print(f"Output: {OUTPUT_FILE}")
print(data.head())
