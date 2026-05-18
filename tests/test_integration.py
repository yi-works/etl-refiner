import polars as pl

from pipeline.data_refiner import DataRefiner


def test_real_config_file():
    import tomllib

    with open("configs/sample.toml", "rb") as f:
        config = tomllib.load(f)

    df = pl.DataFrame({"userid": [1], "status": ["active"]}).lazy()

    refiner = DataRefiner(config)
    result = refiner.process(df, "test").collect()

    assert result.shape[0] >= 0  # smoke test
