import pandas as pd

ref_path = "pipeline/data/suburb_reference.csv"
rent_path = "pipeline/data/2021Census_G02_AUST_SAL.csv"

ref = pd.read_csv(ref_path)
rent_df = pd.read_csv(rent_path)

# Standardise join keys
ref["sal_code_2021"] = ref["sal_code_2021"].astype(str)
rent_df["SAL_CODE_2021"] = rent_df["SAL_CODE_2021"].astype(str)

# Remove any old/duplicate rent columns before merging
for col in ["median_rent_weekly", "Median_rent_weekly", "Median_rent_weekly_x", "Median_rent_weekly_y"]:
    if col in ref.columns:
        ref = ref.drop(columns=[col])

# Keep only the needed ABS columns
rent_df = rent_df[["SAL_CODE_2021", "Median_rent_weekly"]]

# Merge
merged = ref.merge(
    rent_df,
    left_on="sal_code_2021",
    right_on="SAL_CODE_2021",
    how="left"
)

# Clean up
merged = merged.drop(columns=["SAL_CODE_2021"])
merged = merged.rename(columns={"Median_rent_weekly": "median_rent_weekly"})

# Save back
merged.to_csv(ref_path, index=False)

print("✅ Rent successfully added to pipeline/data/suburb_reference.csv")
print(merged.columns.tolist())