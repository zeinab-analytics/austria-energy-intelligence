
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "processed" / "consumption_monthly.csv"
OUTPUT_FILE = BASE_DIR / "reports" / "consumption_trend.png"

# Load validated consumption data
df = pd.read_csv(INPUT_FILE, parse_dates=["month"])
df = df.sort_values("month")

# Convert MWh to GWh
df["consumption_gwh"] = df["consumption_mwh"] / 1000

# Create visualization
fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(
    df["month"],
    df["consumption_gwh"],
    linewidth=1.8,
    color="steelblue",
    label="Monthly Consumption"
)

ax.set_title(
    "Austria — Monthly Electricity Consumption (2010–2026)",
    fontsize=15,
    fontweight="bold"
)

ax.set_xlabel("Year")
ax.set_ylabel("Electricity Consumption (GWh)")

ax.xaxis.set_major_locator(mdates.YearLocator(2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.grid(True, alpha=0.3)
ax.legend()

fig.tight_layout()

# Save chart
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUTPUT_FILE, dpi=150)

plt.show()

print(f"Chart saved successfully: {OUTPUT_FILE}")
