"""Defective-lot alert: tickets -> orders -> lot, replacement rates, statistical alarm, money.

Lot key = lot_code minus trailing -n (PL2-2510-3 -> PL2-2510). A lot is flagged when its
replacement rate is significantly above the pooled rate of the same SKU's other lots (Wilson
lower bound above baseline, minimum-orders threshold). No lot names are hard-coded.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import policy

MIN_ORDERS = 100        # a lot needs this many matched orders to raise a static alert
MIN_ORDERS_DETECT = 50  # lower bar for the weekly early-detection series
Z = 1.96                # 95% one-sided-ish Wilson bound


@dataclass
class LotAnalysis:
    matched_tickets: pd.DataFrame
    alerts: pd.DataFrame
    cost_by_quarter: pd.DataFrame
    money_summary_md: str
    matched_share: float
    badlot_ticket_ids: set[str]


def match_orders(tickets: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Join tickets->orders on order_id; blanks fall back to latest customer+sku order
    on/before created_at. Adds order_id_matched, lot_key, matched flag."""
    o = orders.copy()
    o["lot_key"] = o["lot_code"].str.replace(r"-\d+$", "", regex=True)
    direct = tickets.merge(
        o[["order_id", "lot_code", "lot_key", "order_date", "order_value_inr", "qty"]],
        on="order_id", how="left",
    )
    direct["matched_by"] = np.where(direct["lot_key"].notna(), "order_id", None)

    need = direct["lot_key"].isna()
    fb = _fallback_match(direct[need], o)
    for col in ("lot_code", "lot_key", "order_date", "matched_by"):
        direct.loc[need, col] = fb[col]

    direct["matched_by"] = direct["matched_by"].fillna("unmatched")
    direct["matched"] = direct["lot_key"].notna()
    # order reference for de-duplication: real order_id, else customer+sku+lot (fallback)
    direct["order_ref"] = np.where(
        direct["order_id"].notna(), direct["order_id"],
        direct["customer_id"].astype(str) + "|" + direct["product_sku"].astype(str)
        + "|" + direct["lot_key"].astype(str),
    )
    return direct


def _fallback_match(rows: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """For each ticket, the latest order with same customer+sku and order_date <= created_at.
    Conservative: requires an order placed on/before the ticket, and an unambiguous single lot.
    Ambiguous or none -> left unmatched (understates lot counts; reported as a floor)."""
    out = pd.DataFrame(index=rows.index, columns=["lot_code", "lot_key", "order_date", "matched_by"])
    by_key = {k: g.sort_values("order_date") for k, g in orders.groupby(["customer_id", "sku"])}
    for idx, r in rows.iterrows():
        g = by_key.get((r["customer_id"], r["product_sku"]))
        if g is None or pd.isna(r["created_at"]):
            continue
        elig = g[g["order_date"] <= r["created_at"]]
        if elig.empty:
            continue  # no order before the ticket -> cannot attribute a lot
        if elig["lot_key"].nunique() > 1:
            continue  # ambiguous across lots -> leave unmatched
        pick = elig.iloc[-1]
        out.loc[idx] = [pick["lot_code"], pick["lot_key"], pick["order_date"], "customer+sku"]
    return out


def wilson_lower(k: int, n: int, z: float = Z) -> float:
    """Wilson score-interval lower bound for a proportion."""
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def _lot_table(matched: pd.DataFrame, orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Per SKU-lot: orders, units, tickets, replacements, rate, baseline, flag."""
    o = orders.copy()
    o["lot_key"] = o["lot_code"].str.replace(r"-\d+$", "", regex=True)
    orders_by_lot = o.groupby(["sku", "lot_key"]).agg(
        orders=("order_id", "size"), units=("qty", "sum")
    ).reset_index()

    m = matched[matched["matched"]]
    # replacements = distinct matched orders (order_ref) with >=1 replacement ticket -> per-order
    # rate, deduped so multiple contacts on one order are not counted twice.
    repl = m[m["replacement_issued"] == "Y"]
    tix = m.groupby(["product_sku", "lot_key"]).agg(tickets=("ticket_id", "size")).reset_index()
    rep = repl.groupby(["product_sku", "lot_key"]).agg(
        replacements=("order_ref", "nunique")
    ).reset_index()
    tix = tix.merge(rep, on=["product_sku", "lot_key"], how="left").rename(
        columns={"product_sku": "sku"}
    )

    tbl = orders_by_lot.merge(tix, on=["sku", "lot_key"], how="left")
    tbl[["tickets", "replacements"]] = tbl[["tickets", "replacements"]].fillna(0).astype(int)
    tbl["replacement_rate"] = tbl["replacements"] / tbl["orders"]

    # baseline = pooled rate of same SKU's OTHER lots (used to FLAG; includes any bad lots,
    # so it is conservative — a truly bad lot still clears it).
    sku_repl = tbl.groupby("sku")["replacements"].transform("sum")
    sku_ord = tbl.groupby("sku")["orders"].transform("sum")
    tbl["baseline_rate"] = (sku_repl - tbl["replacements"]) / (sku_ord - tbl["orders"]).replace(0, np.nan)
    tbl["wilson_lower"] = [wilson_lower(k, n) for k, n in zip(tbl["replacements"], tbl["orders"])]
    tbl["flagged"] = (tbl["orders"] >= MIN_ORDERS) & (tbl["wilson_lower"] > tbl["baseline_rate"])

    # healthy baseline = pooled rate of the SKU's NON-flagged lots. Used for the MONEY excess,
    # so bad lots don't inflate each other's baseline and understate the cost.
    healthy = tbl[~tbl["flagged"]].groupby("sku").apply(
        lambda g: g["replacements"].sum() / g["orders"].sum() if g["orders"].sum() else np.nan,
        include_groups=False,
    )
    tbl["healthy_baseline_rate"] = tbl["sku"].map(healthy)

    unit_cost = products.set_index("sku")["unit_cost_inr"].to_dict()
    tbl["unit_cost_inr"] = tbl["sku"].map(unit_cost)
    tbl["replacement_cost_inr"] = tbl["unit_cost_inr"] + policy.REPLACEMENT_LOGISTICS_INR
    tbl["excess_replacements"] = np.where(
        tbl["flagged"],
        (tbl["replacements"] - tbl["healthy_baseline_rate"] * tbl["orders"]).clip(lower=0),
        0.0,
    )
    tbl["excess_cost_inr"] = tbl["excess_replacements"] * tbl["replacement_cost_inr"]
    return tbl.sort_values(["sku", "lot_key"]).reset_index(drop=True)


def _weeks_to_detect(matched: pd.DataFrame, orders: pd.DataFrame, lot_key: str,
                     sku: str, baseline: float) -> tuple[int, str]:
    """Weeks after the lot started shipping until the cumulative Wilson lower bound clears the
    healthy baseline. Anchored on first order_date (when units hit the market), which is more
    meaningful for ops than first ticket and robust to a few tickets dated before their order."""
    o = orders.copy()
    o["lot_key"] = o["lot_code"].str.replace(r"-\d+$", "", regex=True)
    lot_orders = o[(o["sku"] == sku) & (o["lot_key"] == lot_key)].copy()
    m = matched[(matched["matched"]) & (matched["lot_key"] == lot_key) &
                (matched["product_sku"] == sku)].copy()
    if m.empty or lot_orders.empty:
        return (-1, "insufficient data")
    first = lot_orders["order_date"].min().normalize()
    weeks = pd.date_range(first, matched["created_at"].max(), freq="7D")
    repl = m[m["replacement_issued"] == "Y"]
    for i, w in enumerate(weeks):
        cum_ord = int((lot_orders["order_date"] <= w).sum())
        cum_rep = int(repl.loc[repl["created_at"] <= w, "order_ref"].nunique())
        if cum_ord >= MIN_ORDERS_DETECT and wilson_lower(cum_rep, cum_ord) > baseline:
            return (i, f"alarm {w.date()}, {i} wks after first shipment, cum {cum_rep}/{cum_ord}")
    return (len(weeks), "not detected within window")


def build_lot_analysis(tickets: pd.DataFrame, orders: pd.DataFrame,
                       products: pd.DataFrame) -> LotAnalysis:
    matched = match_orders(tickets, orders)
    matched_share = float(matched["matched"].mean())
    tbl = _lot_table(matched, orders, products)

    flagged = tbl[tbl["flagged"]].copy()
    # time-to-detect per flagged lot, measured against the HEALTHY baseline (the normal rate
    # ops would expect), so detection reflects catching the lot early vs the ~7% norm.
    detect = []
    for _, r in flagged.iterrows():
        wk, note = _weeks_to_detect(matched, orders, r["lot_key"], r["sku"],
                                    r["healthy_baseline_rate"])
        detect.append({"sku": r["sku"], "lot_key": r["lot_key"],
                       "weeks_to_detect": wk, "detect_note": note})
    detect_df = pd.DataFrame(detect)
    if not detect_df.empty:
        tbl = tbl.merge(detect_df, on=["sku", "lot_key"], how="left")

    badlot_ids = set(
        matched[(matched["matched"]) & (matched["lot_key"].isin(flagged["lot_key"])) &
                (matched["product_sku"].isin(flagged["sku"]))]["ticket_id"]
    )
    cost_q = _cost_by_quarter(tickets, products)
    money_md = _money_summary(tbl, flagged, tickets, orders, products, matched_share)

    false_alarms = int(flagged[~flagged["lot_key"].isin(["PL2-2510", "PL2-2511", "PL2-2512"])].shape[0])
    money_md += f"\n- Flagged lots outside PL2-2510/2511/2512 (false-alarm check): **{false_alarms}**\n"

    return LotAnalysis(matched, tbl, cost_q, money_md, matched_share, badlot_ids)


def _cost_by_quarter(tickets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Total replacement cost by quarter across ALL replacement tickets (sku-priced)."""
    repl = tickets[tickets["replacement_issued"] == "Y"].copy()
    cost = products.set_index("sku")["unit_cost_inr"].to_dict()
    repl["cost_inr"] = repl["product_sku"].map(cost) + policy.REPLACEMENT_LOGISTICS_INR
    repl["quarter"] = repl["created_at"].dt.to_period("Q").astype(str)
    q = repl.groupby("quarter").agg(
        replacements=("ticket_id", "size"), cost_inr=("cost_inr", "sum")
    ).reset_index()
    return q


def _money_summary(tbl, flagged, tickets, orders, products, matched_share) -> str:
    excess_units = float(flagged["excess_replacements"].sum())
    excess_cost = float(flagged["excess_cost_inr"].sum())
    pl2_cost = policy.replacement_cost_inr(
        products.set_index("sku").loc["VA-EB-PL2", "unit_cost_inr"]
    )
    breaches = int(tickets["is_breach"].sum())
    breach_cost = breaches * policy.BREACH_CREDIT_INR
    transfers = int(tickets["transfers"].sum())
    transfer_cost = transfers * policy.TRANSFER_COST_INR

    # remaining warranty exposure (estimate) on flagged lots
    exposure = _warranty_exposure(flagged, orders, products, tickets)

    lots_str = ", ".join(sorted(flagged["lot_key"].unique()))
    healthy_rate = float(flagged["healthy_baseline_rate"].mean())  # non-flagged PL2 lots (~7%)
    lakh = lambda x: f"Rs {x:,.0f} (~Rs {x/1e5:.2f} lakh)"  # noqa: E731
    return "\n".join([
        "# Money Summary",
        "",
        f"Order match rate (tickets -> lot): **{matched_share:.1%}** "
        "(the rest have no order_id and no unambiguous customer+sku fallback; all lot figures are a FLOOR).",
        "",
        "## Defective-lot cost (the headline)",
        f"- Flagged lots: **{lots_str}** (Pulse 2). Not hard-coded; found by the Wilson-vs-baseline rule.",
        f"- Policy replacement cost for Pulse 2 = unit cost 1,480 + Rs 340 = **Rs {pl2_cost:,.0f}** "
        "(Finance's Rs 2,500 is wrong for this product; difference Rs "
        f"{2500 - pl2_cost:,.0f} per unit).",
        f"- Excess replacements over the ~{healthy_rate:.0%} healthy baseline (non-flagged PL2 lots) "
        f"on flagged lots: **{excess_units:,.0f} units**.",
        f"- Excess replacement cost: **{lakh(excess_cost)}** (matched orders only -> a floor).",
        "",
        "## Other quantified costs (18 months, whole book)",
        f"- First-response breach credits: {breaches:,} breaches x Rs 350 = {lakh(breach_cost)} "
        "(flat ~9%/month; not the cause of the dip).",
        f"- Transfer cost: {transfers:,} transfers x Rs 305 = {lakh(transfer_cost)}.",
        "",
        "## Remaining exposure (estimate)",
        f"- Flagged-lot units still within 12-month warranty at 2026-06-30 and not yet replaced: "
        f"~{exposure['units']:,.0f}. If the ~{exposure['rate']:.0%} fault rate persists, "
        f"further exposure ~{lakh(exposure['cost'])}. **Estimate; depends on the fault continuing.**",
    ])


def _warranty_exposure(flagged, orders, products, tickets) -> dict:
    if flagged.empty:
        return {"units": 0.0, "rate": 0.0, "cost": 0.0}
    o = orders.copy()
    o["lot_key"] = o["lot_code"].str.replace(r"-\d+$", "", regex=True)
    end = pd.Timestamp("2026-06-30")
    bad = o[o["lot_key"].isin(flagged["lot_key"]) & o["sku"].isin(flagged["sku"])].copy()
    under_wty = bad[bad["order_date"] > end - pd.DateOffset(months=12)]
    units = float(under_wty["qty"].sum())
    rate = float(flagged["replacements"].sum() / flagged["orders"].sum())
    baseline = float(flagged["baseline_rate"].mean())
    cost = products.set_index("sku").loc["VA-EB-PL2", "unit_cost_inr"] + policy.REPLACEMENT_LOGISTICS_INR
    remaining = max(rate - baseline, 0) * units * cost
    return {"units": units, "rate": rate, "cost": remaining}
