import time
import polars as pl
import pytest
from pipeline.data_refiner import DataRefiner


@pytest.mark.parametrize("size", [1000, 10000, 100000])
def test_benchmark(size):
    if size == 1000:
        print("\n| Rows | Time |")
        print("|------|------|")

    df = pl.DataFrame({"amount": range(size)}).lazy()

    config = {
        "test": {
            "derive": [
                {
                    "op": "compare",
                    "src": "amount",
                    "op_type": ">",
                    "val": 500,
                    "dst": "flag",
                }
            ]
        }
    }

    refiner = DataRefiner(config)

    refiner.process(df, "test").collect()

    runs = 5
    times = []

    for _ in range(runs):
        start = time.perf_counter()
        refiner.process(df, "test").collect()
        times.append(time.perf_counter() - start)

    # ✅ 平均
    avg = sum(times) / len(times)

    print(f"| {size:,} | ~{avg:.6f}s |")
