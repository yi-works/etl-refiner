from typing import Dict
import polars as pl


def op_map(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    expr = pl.col(s["src"]).cast(pl.String).str.to_lowercase()
    branch = pl.when(False).then(pl.lit(None))
    for k, v in s["mapping"].items():
        branch = branch.when(expr == k.lower()).then(pl.lit(v))
    return lf.with_columns(
        branch.otherwise(pl.lit(s.get("default", "Unknown"))).alias(s["dst"])
    )


def op_is_in(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    return lf.with_columns(
        pl.col(s["src"]).is_in(s["list"]).cast(pl.Int32).alias(s["dst"]),
    )


def op_compare(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    val = s["val"]
    op = s["op_type"]
    col = pl.col(s["src"]).cast(pl.Float64, strict=False)
    expr = {
        ">": col > val,
        "<": col < val,
        ">=": col >= val,
        "<=": col <= val,
        "==": col == val,
    }.get(op, col == val)
    return lf.with_columns(
        expr.cast(pl.Int32).alias(s["dst"]),
    )


def op_filter(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    col = pl.col(s["src"]).cast(pl.Utf8).str.to_lowercase()
    op_type = s.get("op_type", "eq")
    if op_type == "eq":
        return lf.filter(col == str(s["val"]).lower())
    elif op_type == "ne":
        return lf.filter(col != str(s["val"]).lower())
    elif op_type == "in":
        vals = [str(v).lower() for v in s["list"]]
        return lf.filter(col.is_in(vals))
    elif op_type == "not_in":
        vals = [str(v).lower() for v in s["list"]]
        return lf.filter(~col.is_in(vals))
    else:
        raise ValueError(f"unsupported filter op_type: {op_type}")


def op_const(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    return lf.with_columns(
        pl.lit(s["val"]).cast(pl.Int32).alias(s["dst"]),
    )


def op_extract_localpart(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:
    return lf.with_columns(
        pl.col(s["src"]).cast(pl.Utf8).str.split("@").list.get(0).alias(s["dst"])
    )


def op_add_date_col_ret(lf: pl.LazyFrame, s: Dict) -> pl.LazyFrame:

    src = s["src"]
    calendar_lf: pl.LazyFrame = s["calendar_lf"]
    assert isinstance(calendar_lf, pl.LazyFrame), type(calendar_lf)

    day_name_col = s.get("day_name_col", "day_name")
    cal_yw_col = s.get("calendar_yearweek_col", "year+week")
    dst_yearweek = s.get("dst_yearweek", "year_week")

    lf = lf.with_columns(
        (
            pl.col(src).str.split("-").list.get(0).cast(pl.Int32) * 100
            + pl.col(src).str.split("-").list.get(1).cast(pl.Int32)
        ).alias(dst_yearweek)
    )

    return lf.join(
        calendar_lf.select(
            [
                pl.col(cal_yw_col).alias(dst_yearweek),
                day_name_col,
                "date",
            ]
        ),
        on=[dst_yearweek, day_name_col],
        how="left",
    )


DISPATCHER = {
    "map": op_map,
    "is_in": op_is_in,
    "compare": op_compare,
    "const": op_const,
    "filter": op_filter,
    "extract_localpart": op_extract_localpart,
    "add_date_col_ret": op_add_date_col_ret,
}
