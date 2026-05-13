import geopandas as gpd
import pandas as pd

# Load shapefile
gdf = gpd.read_file("pipeline/data/sal/SAL_2021_AUST_GDA2020.shp")

# Convert to projected CRS for area calculation
gdf = gdf.to_crs(epsg=3857)

# Calculate area in km²
gdf["suburb_area_sq_km"] = gdf.geometry.area / 1_000_000

# Select required columns, INCLUDING SAL code
df = gdf[[
    "SAL_CODE21",
    "SAL_NAME21",
    "STE_NAME21",
    "suburb_area_sq_km"
]].copy()

# Rename columns
df.rename(columns={
    "SAL_CODE21": "sal_code_2021",
    "SAL_NAME21": "name",
    "STE_NAME21": "state"
}, inplace=True)

# Map full state names to abbreviations
STATE_MAP = {
    "New South Wales": "NSW",
    "Victoria": "VIC",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Western Australia": "WA",
    "Tasmania": "TAS",
    "Australian Capital Territory": "ACT",
    "Northern Territory": "NT"
}

df["state"] = df["state"].map(STATE_MAP)

# Clean suburb names
df["name"] = df["name"].str.title().str.strip()

# Round area
df["suburb_area_sq_km"] = df["suburb_area_sq_km"].round(2)

# Placeholder population
df["population"] = pd.NA

# Reorder columns
df = df[["sal_code_2021", "name", "state", "population", "suburb_area_sq_km"]]

# Save
df.to_csv("suburb_reference.csv", index=False)

print("✅ suburb_reference.csv created!")

# Test suburbs
test_suburbs = [
    ("Glen Waverley", "VIC"),
    ("Roxburgh Park", "VIC"),
    ("Bendigo", "VIC"),
    ("Melton South", "VIC"),
]

print("\n🔍 Testing suburb areas:\n")

for suburb, state in test_suburbs:
    match = df[(df["name"] == suburb) & (df["state"] == state)]

    if not match.empty:
        row = match.iloc[0]
        print(
            f"{suburb}, {state} → SAL: {row['sal_code_2021']} | "
            f"Area: {row['suburb_area_sq_km']} km²"
        )
    else:
        print(f"{suburb}, {state} → ❌ NOT FOUND")