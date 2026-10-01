"""Load raw CSVs and parse types. Read-only on data/raw. Fail loudly on surprises."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import policy

TS_FORMAT = "%Y-%m-%d %H:%M"
TS_COLS = ["created_at", "first_response_at", "resolved_at"]


@dataclass
class RawData:
    tickets: pd.DataFrame
    orders: pd.DataFrame
    customers: pd.DataFrame
    agents: pd.DataFrame
    products: pd.DataFrame


def _parse_ts(series: pd.Series, col: str) -> pd.Series:
    """Parse a timestamp column with a fixed format. Blanks stay NaT; non-blank that
    fail to parse raise (never coerce silently)."""
    parsed = pd.to_datetime(series, format=TS_FORMAT, errors="coerce")
    bad = series.notna() & series.astype(str).str.strip().ne("") & parsed.isna()
    if bad.any():
        examples = series[bad].head(3).tolist()
        raise ValueError(f"Unparseable timestamps in {col!r}: {examples}")
    return parsed


def load_raw(data_dir: str | Path) -> RawData:
    """Read the five CSVs, parse types, assert row counts. utf-8, quoted multiline messages."""
    d = Path(data_dir)
    read = lambda name: pd.read_csv(  # noqa: E731
        d / name, dtype=str, encoding="utf-8", keep_default_na=True, na_values=[""]
    )

    tickets = read("tickets.csv")
    orders = read("orders.csv")
    customers = read("customers.csv")
    agents = read("agents.csv")
    products = read("products.csv")

    _assert_counts(
        {"tickets": tickets, "orders": orders, "customers": customers,
         "agents": agents, "products": products}
    )

    for col in TS_COLS:
        tickets[col] = _parse_ts(tickets[col], col)

    # numeric fields — coerce known-numeric only, then verify no silent losses
    tickets["csat_score"] = _to_num(tickets["csat_score"], "csat_score")
    tickets["transfers"] = _to_num(tickets["transfers"], "transfers").fillna(0).astype(int)
    tickets["refund_amount_inr"] = _to_num(tickets["refund_amount_inr"], "refund_amount_inr")

    orders["qty"] = _to_num(orders["qty"], "qty")
    orders["order_value_inr"] = _to_num(orders["order_value_inr"], "order_value_inr")
    orders["order_date"] = pd.to_datetime(orders["order_date"], format="%Y-%m-%d", errors="raise")

    for c in ("unit_cost_inr", "retail_price_inr", "warranty_months"):
        products[c] = _to_num(products[c], c)

    return RawData(tickets, orders, customers, agents, products)


def _to_num(series: pd.Series, col: str) -> pd.Series:
    parsed = pd.to_numeric(series, errors="coerce")
    bad = series.notna() & parsed.isna()
    if bad.any():
        raise ValueError(f"Non-numeric values in {col!r}: {series[bad].head(3).tolist()}")
    return parsed


def _assert_counts(frames: dict[str, pd.DataFrame]) -> None:
    for name, df in frames.items():
        expected = policy.EXPECTED_ROW_COUNTS[name]
        if len(df) != expected:
            raise AssertionError(f"{name}: expected {expected} rows, got {len(df)}")
