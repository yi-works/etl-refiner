import polars as pl
import pytest

from pipeline.data_refiner import DataRefiner


@pytest.fixture
def sample_df():
    return pl.DataFrame(
        {
            "USER ID": [1, 2],
            "CreatedAt": ["2024-01-01", "2024-01-02"],
            "status": ["active", "inactive"],
            "amount": [500, 2000],
        }
    ).lazy()


@pytest.fixture
def config():
    return {
        "test": {
            "rename": {
                "user id": "user_id",
                "createdat": "created_at",
            },
            "date": {"source": "created_at"},
            "defaults": {"country": "unknown"},
            "derive": [
                {
                    "op": "compare",
                    "src": "amount",
                    "op_type": ">",
                    "val": 1000,
                    "dst": "is_high",
                }
            ],
            "filters": [{"col": "status", "op": "ne", "val": "inactive"}],
        }
    }


# 基本処理テスト
def test_pipeline_basic(sample_df, config):
    refiner = DataRefiner(config)

    result = refiner.process(sample_df, "test").collect()

    # フィルタで1行になるか
    assert result.shape[0] == 1

    # 列が正しく変換されているか
    assert "user_id" in result.columns
    assert "date" in result.columns
    assert "country" in result.columns
    assert "is_high" in result.columns


# rename検証
def test_rename(sample_df, config):
    refiner = DataRefiner(config)
    result = refiner.process(sample_df, "test").collect()

    assert "user_id" in result.columns
    assert "created_at" in result.columns


# 日付変換
def test_date_parsing(sample_df, config):
    refiner = DataRefiner(config)
    result = refiner.process(sample_df, "test").collect()

    assert result["date"].dtype == pl.Date


# default値
def test_defaults(sample_df, config):
    refiner = DataRefiner(config)
    result = refiner.process(sample_df, "test").collect()

    assert result["country"][0] == "unknown"


# derive（compare）
def test_derive_compare(sample_df, config):
    refiner = DataRefiner(config)
    result = refiner.process(sample_df, "test").collect()

    # inactiveはfilterされているので1行だけ
    assert result["is_high"][0] in (0, 1)


# filter動作
def test_filter(sample_df, config):
    refiner = DataRefiner(config)
    result = refiner.process(sample_df, "test").collect()

    assert all(result["status"] != "inactive")


# 空configでも落ちないか
def test_empty_config(sample_df):
    refiner = DataRefiner({"test": {}})
    result = refiner.process(sample_df, "test").collect()

    assert result.shape[0] == 2
