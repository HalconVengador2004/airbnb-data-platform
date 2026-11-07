import pandas as pd

files = {
    "Madrid": "data/raw/listings_madrid.csv",
    "Euskadi": "data/raw/listings_euskadi.csv"
}
datasets = {}

for city, path in files.items():
    datasets[city] = pd.read_csv(path, low_memory=False)

    df = datasets[city]

    print(f"\n{'=' * 50}")
    print(f"CITY: {city}")
    print(f"{'=' * 50}")

    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print("\nColumn types:")
    print(df.dtypes)
    print("\nMissing values:")
    print(df.isna().sum().sort_values(ascending=False).head(15))
    print("\nSample:")
    print(df.head(3))
    
madrid = datasets["Madrid"]
euskadi = datasets["Euskadi"]

print("\nDUPLICATE IDS")
for city, df in datasets.items():
    print(f"{city}: {df['id'].duplicated().sum()}")

print("\nCOLUMN DIFFERENCES")
print("Only Madrid:", sorted(set(madrid.columns) - set(euskadi.columns)))
print("Only Euskadi:", sorted(set(euskadi.columns) - set(madrid.columns)))

print("\nDATA TYPE DIFFERENCES")
for column in sorted(set(madrid.columns) & set(euskadi.columns)):
    if madrid[column].dtype != euskadi[column].dtype:
        print(
            f"{column}: Madrid={madrid[column].dtype}, "
            f"Euskadi={euskadi[column].dtype}"
        )

print("\nCOMPLETELY NULL COLUMNS")
for city, df in datasets.items():
    print(f"{city}: {df.columns[df.isna().all()].tolist()}")