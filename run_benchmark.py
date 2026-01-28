import time
import json
import psutil
import os
import gc
import sys
from pathlib import Path
import warnings
import numpy as np

import pandas as pd
import polars as pl

warnings.filterwarnings("ignore")

# --- MANUAL TOGGLE FOR EXPERIMENTS ---
RUN_MODE = "polars"  # "pandas2", "pandas3", or "polars"
RUN_ID = "run1"
# -------------------------------------

DATA_DIR = Path("data")
OUT_DIR = Path("benchmark_results")
OUT_DIR.mkdir(exist_ok=True)

# These match your new data_prep.py outputs
BIG_CSV = DATA_DIR / "big_mixed_medium.csv"
LEFT_PARQUET = DATA_DIR / "left.parquet"
RIGHT_PARQUET = DATA_DIR / "right.parquet"

process = psutil.Process(os.getpid())


def current_mem_mb():
    return process.memory_info().rss / (1024 ** 2)


class BenchmarkTimer:
    def __init__(self, name=""):
        self.name = name
        self.elapsed = 0
        self.peak_mem = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.start_mem = current_mem_mb()
        self.peak_mem = self.start_mem
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start_time
        self.peak_mem = max(self.peak_mem, current_mem_mb())
        print(f"{self.name}: {self.elapsed:.3f}s | Peak: {self.peak_mem:.1f}MB")
        return False


results = {
    "backend": RUN_MODE,
    "run_id": RUN_ID,
    "versions": {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "polars": pl.__version__
    },
    "partA": {}, "partB": {}, "partC": {}
}


def run():
    print(f"--- Starting Benchmark Iteration: {RUN_MODE} ---")
    print(f"Versions -> Python: {results['versions']['python']} | Pandas: {pd.__version__} | Polars: {pl.__version__}")

    if RUN_MODE.startswith("pandas"):
        pd.options.mode.copy_on_write = True

    # --- Part A: Reads (Now testing ~4GB CSV) ---
    with BenchmarkTimer("CSV Read") as t:
        if RUN_MODE == "pandas3":
            df = pd.read_csv(BIG_CSV, engine="pyarrow", dtype_backend="pyarrow")
        elif RUN_MODE == "pandas2":
            df = pd.read_csv(BIG_CSV, low_memory=False)
        else:
            df = pl.read_csv(BIG_CSV)

    results["partA"]["csv_time"] = t.elapsed
    results["partA"]["csv_mem"] = t.peak_mem
    del df
    gc.collect()

    # --- Part B: Slicing (Dynamic Sizing) ---
    if RUN_MODE.startswith("pandas"):
        df_base = pd.read_parquet(LEFT_PARQUET)
    else:
        df_base = pl.read_parquet(LEFT_PARQUET)

    total_slice_time = 0
    max_slice_mem = 0
    num_slices = 10

    # Calculate chunk size for Polars to match Pandas iloc behavior
    chunk_size = len(df_base) // num_slices

    for i in range(num_slices):
        with BenchmarkTimer(f"Slice {i}") as t:
            if RUN_MODE.startswith("pandas"):
                # Slices 1/10th of the data by stepping
                s = df_base.iloc[i::num_slices].copy()
                s['total_amount'] += 0.01
            else:
                # Slices 1/10th of the data by contiguous chunks
                s = df_base.slice(i * chunk_size, chunk_size).with_columns(
                    pl.col("total_amount") + 0.01
                )
        total_slice_time += t.elapsed
        max_slice_mem = max(max_slice_mem, t.peak_mem)

    results["partB"]["slice_time"] = total_slice_time
    results["partB"]["slice_mem"] = max_slice_mem
    del df_base, s
    gc.collect()

    # --- Part C: Join (Testing Hash-Join Performance) ---
    if RUN_MODE.startswith("pandas"):
        left, right = pd.read_parquet(LEFT_PARQUET), pd.read_parquet(RIGHT_PARQUET)
    else:
        left, right = pl.scan_parquet(LEFT_PARQUET), pl.scan_parquet(RIGHT_PARQUET)

    with BenchmarkTimer("Join + GroupBy") as t:
        if RUN_MODE.startswith("pandas"):
            merged = left.merge(right, on=['PULocationID', 'DOLocationID'], how='inner')
            res = merged.groupby('PULocationID')['total_amount'].sum()
        else:
            res = (left.join(right, on=['PULocationID', 'DOLocationID'], how='inner')
                   .group_by('PULocationID')
                   .agg(pl.col('total_amount').sum())
                   .collect())

    results["partC"]["join_time"] = t.elapsed
    results["partC"]["join_mem"] = t.peak_mem

    out_file = OUT_DIR / f"{RUN_MODE}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {out_file}")


if __name__ == "__main__":
    run()