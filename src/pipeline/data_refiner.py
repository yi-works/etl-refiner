import polars as pl
from typing import Dict, Any
from copy import deepcopy

from pipeline.dispatchers import DISPATCHER


class DataRefiner:
    """
    Config-driven ETL preprocessing engine.

    Features:
    - Schema normalization
    - Config-based transformations
    - Lazy execution (Polars LazyFrame)
    - Extensible via dispatcher pattern
    """

    def __init__(self, configs: Dict[str, Dict[str, Any]]):
        self.configs = configs

    # -----------------------------
    # Core Pipeline
    # -----------------------------
    def process(self, lf: pl.LazyFrame, config_name: str) -> pl.LazyFrame:
        cfg = self._resolve_cfg(self.configs.get(config_name, {}))

        lf = self._normalize_columns(lf)
        lf = self._rename(lf, cfg)
        lf = self._apply_date(lf, cfg)
        lf = self._apply_derivations(lf, cfg)
        lf = self._apply_filters(lf, cfg)
        lf = self._apply_defaults(lf, cfg)

        return lf

    # -----------------------------
    # Steps
    # -----------------------------
    def _normalize_columns(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        cols = lf.collect_schema().names()
        return lf.rename({c: c.lower().strip() for c in cols})

    def _rename(self, lf: pl.LazyFrame, cfg: Dict) -> pl.LazyFrame:
        rename_map = {k.lower().strip(): v for k, v in cfg.get("rename", {}).items()}
        schema = lf.collect_schema().names()
        return lf.rename({k: v for k, v in rename_map.items() if k in schema})

    def _apply_date(self, lf: pl.LazyFrame, cfg: Dict) -> pl.LazyFrame:
        date_cfg = cfg.get("date", {})

        src = date_cfg.get("source")
        target = date_cfg.get("target", "date")

        if src and src in lf.collect_schema().names():
            lf = lf.with_columns(pl.col(src).alias(target))

        if target in lf.collect_schema().names():
            lf = lf.with_columns(
                pl.col(target).cast(pl.Utf8).str.slice(0, 10).str.to_date(strict=False)
            )

        return lf

    def _apply_derivations(self, lf: pl.LazyFrame, cfg: Dict) -> pl.LazyFrame:
        for step in cfg.get("derive", []):
            op = step.get("op")
            if op in DISPATCHER:
                lf = DISPATCHER[op](lf, step)
        return lf

    def _apply_filters(self, lf: pl.LazyFrame, cfg: Dict) -> pl.LazyFrame:
        filters = cfg.get("filters", [])
        for f in filters:
            col = pl.col(f["col"])
            op = f.get("op", "eq")
            val = f.get("val")

            if op == "eq":
                lf = lf.filter(col == val)
            elif op == "ne":
                lf = lf.filter(col != val)
            elif op == "in":
                lf = lf.filter(col.is_in(val))
            elif op == "not_in":
                lf = lf.filter(~col.is_in(val))
            else:
                raise ValueError(f"Unsupported filter op: {op}")

        return lf

    def _apply_defaults(self, lf: pl.LazyFrame, cfg: Dict) -> pl.LazyFrame:
        schema = lf.collect_schema().names()
        exprs = []

        for col, val in cfg.get("defaults", {}).items():
            if col not in schema:
                exprs.append(pl.lit(val).alias(col))

        if exprs:
            lf = lf.with_columns(exprs)

        return lf

    # -----------------------------
    # Config handling
    # -----------------------------
    def _resolve_cfg(self, cfg: Dict) -> Dict:
        return deepcopy(cfg)
