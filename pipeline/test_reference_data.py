import pandas as pd

REFERENCE_CSV = "suburb_reference.csv"

test_suburbs = [
    ("Glen Waverley", "VIC"),
    ("Roxburgh Park", "VIC"),
    ("Bendigo", "VIC"),
    ("Melton South", "VIC"),
    ("Richmond", "VIC"),
    ("Richmond North", "VIC"),
    ("Richmond South", "VIC"),
    ("Carlton", "VIC"),
    ("Fitzroy", "VIC"),
    ("Preston", "VIC"),
    ("Sydney", "NSW"),
    ("South Brisbane", "QLD"),
]

df = pd.read_csv(REFERENCE_CSV)

print("Columns:")
print(df.columns.tolist())
print(f"\nTotal rows: {len(df)}")

print("\nChecking test suburbs:\n")

for suburb, state in test_suburbs:
    match = df[(df["name"] == suburb) & (df["state"] == state)]

    if not match.empty:
        row = match.iloc[0]
        density = None
        if pd.notna(row["population"]) and pd.notna(row["suburb_area_sq_km"]) and row["suburb_area_sq_km"] != 0:
            density = row["population"] / row["suburb_area_sq_km"]

        print(
            f"{suburb}, {state} -> "
            f"SAL: {row['sal_code_2021']} | "
            f"Population: {row['population']} | "
            f"Area: {row['suburb_area_sq_km']} km² | "
            f"Density: {round(density, 2) if density is not None else 'N/A'} per km²"
        )
    else:
        print(f"{suburb}, {state} -> NOT FOUND")

print("\nAny missing population rows?")
missing_pop = df[df["population"].isna()]
print(missing_pop[["sal_code_2021", "name", "state"]].head(20).to_string(index=False))
print(f"\nMissing population count: {len(missing_pop)}")