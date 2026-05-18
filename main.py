import sys
import tomllib
import polars as pl

from pipeline.data_refiner import DataRefiner


def main():
    if len(sys.argv) < 3:
        print("Usage: python main.py <input.csv> <config.toml>")
        sys.exit(1)

    input_path = sys.argv[1]
    config_path = sys.argv[2]

    # Load config
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # Load data
    lf = pl.scan_csv(input_path)

    # Process
    refiner = DataRefiner(config)
    result = refiner.process(lf, "test")

    # Output
    print(result.collect())


if __name__ == "__main__":
    main()
