import pandas as pd

REFERENCE_CSV = "suburb_reference.csv"
CENSUS_CSV = "pipeline/data/2021Census_G01_AUST_SAL.csv"

def standardize_sal_code(value):
    if pd.isna(value):
        return pd.NA

    s = str(value).strip().upper()

    # remove SAL prefix if present
    if s.startswith("SAL"):
        s = s[3:]

    # keep digits only
    s = "".join(ch for ch in s if ch.isdigit())

    if not s:
        return pd.NA

    return f"SAL{s.zfill(5)}"

# Load files
ref_df = pd.read_csv(REFERENCE_CSV)
census_df = pd.read_csv(CENSUS_CSV)

print("Reference columns:", ref_df.columns.tolist())
print("Census columns:", census_df.columns.tolist()[:10])

# Standardise codes
ref_df["sal_code_2021"] = ref_df["sal_code_2021"].apply(standardize_sal_code)
census_df["SAL_CODE_2021"] = census_df["SAL_CODE_2021"].apply(standardize_sal_code)

print("\nSample suburb_reference SAL codes:")
print(ref_df["sal_code_2021"].head(10).tolist())

print("\nSample census SAL codes:")
print(census_df["SAL_CODE_2021"].head(10).tolist())

# Build population table
pop_df = census_df[["SAL_CODE_2021", "Tot_P_P"]].copy()
pop_df.rename(columns={
    "SAL_CODE_2021": "sal_code_2021",
    "Tot_P_P": "population"
}, inplace=True)

# Merge
merged = ref_df.drop(columns=["population"], errors="ignore").merge(
    pop_df,
    on="sal_code_2021",
    how="left"
)

# Reorder
merged = merged[["sal_code_2021", "name", "state", "population", "suburb_area_sq_km"]]

# Save
merged.to_csv(REFERENCE_CSV, index=False)

print("\n✅ Population added to suburb_reference.csv")
print(f"Matched populations: {merged['population'].notna().sum()} / {len(merged)}")

# Quick tests
test_suburbs = [
    ("Glen Waverley", "VIC"),
    ("Roxburgh Park", "VIC"),
    ("Bendigo", "VIC"),
    ("Melton South", "VIC"),
]

print("\n🔍 Testing suburb populations:\n")

for suburb, state in test_suburbs:
    match = merged[(merged["name"] == suburb) & (merged["state"] == state)]

    if not match.empty:
        row = match.iloc[0]
        print(
            f"{suburb}, {state} → "
            f"SAL: {row['sal_code_2021']} | "
            f"Population: {row['population']} | "
            f"Area: {row['suburb_area_sq_km']} km²"
        )
    else:
        print(f"{suburb}, {state} → ❌ NOT FOUND")