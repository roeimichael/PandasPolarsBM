import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Sources and Targets
SOURCE_CSV = DATA_DIR / "big_mixed_2gb.csv"
BIG_CSV = DATA_DIR / "big_mixed_medium.csv"  # This will be our 1GB working set
LEFT_PARQUET = DATA_DIR / "left.parquet"
RIGHT_PARQUET = DATA_DIR / "right.parquet"


def prepare_data():
    if not SOURCE_CSV.exists():
        print(f"Error: {SOURCE_CSV} not found in data folder.")
        return

    print(f"Loading 50% of {SOURCE_CSV.name}...")
    # Loading 50% to ensure results aren't too quick
    # We use a fixed chunksize or fraction to manage memory during this prep
    df = pd.read_csv(SOURCE_CSV, low_memory=False)
    df = df.sample(frac=0.5, random_state=42).reset_index(drop=True)

    # Ensure we have a unique ID for the join logic
    if 'unique_row_id' not in df.columns:
        df['unique_row_id'] = np.arange(len(df))

    print(f"New dataset size: {len(df):,} rows.")

    # Save the 1GB-ish working CSV
    print("Saving working CSV...")
    df.to_csv(BIG_CSV, index=False)

    # --- Generate Join Tables ---
    # Left table: full sample (~1.25M - 5M rows depending on your original CSV)
    # Adjust columns if your 2GB CSV has different headers
    cols_left = ['PULocationID', 'DOLocationID', 'passenger_count', 'total_amount', 'unique_row_id']
    left = df[[c for c in cols_left if c in df.columns]].copy()

    # Right table: Unique keys to prevent Cartesian Join MemoryError
    cols_right = ['PULocationID', 'DOLocationID', 'RatecodeID', 'trip_distance']
    right_subset = [c for c in cols_right if c in df.columns]

    right = df[right_subset].drop_duplicates(subset=['PULocationID', 'DOLocationID']).copy()

    print("Saving Parquet files for join tests...")
    left.to_parquet(LEFT_PARQUET, index=False)
    right.to_parquet(RIGHT_PARQUET, index=False)

    print(f"Data ready.")
    print(f"Left: {len(left):,} rows | Right (Unique Keys): {len(right):,} rows")


if __name__ == "__main__":
    # We force run this since we are changing the dataset size
    prepare_data()