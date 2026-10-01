"""Per-agent metrics: CSAT, handle time (per channel), breach, transfers.

Join on agent_id only. Display name is "Name (agent_id)". Tier 2 is measured in
days-to-resolve, never volume, and kept in its own peer group by the ranking layer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import policy

CHANNELS = ["chat", "email", "voice", "social"]


def add_derived(tickets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Add family, first-response minutes, breach flag, csat<=2 flag."""
    t = tickets.copy()
    fam = products.set_index("sku")["family"].to_dict()
    t["family"] = t["product_sku"].map(fam)
    t["first_response_min"] = (
        (t["first_response_at"] - t["created_at"]).dt.total_seconds() / 60.0
    )
    target = t["channel"].map(policy.FIRST_RESPONSE_TARGET_MIN)
    t["is_breach"] = t["first_response_min"] > target
    t["csat_le2"] = t["csat_valid"] & (t["csat_score"] <= 2)
    return t


def display_name(agents: pd.DataFrame) -> pd.Series:
    return agents["name"] + " (" + agents["agent_id"] + ")"


def agent_scorecard(tickets: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """One row per agent (all 44). CSAT with n, handle time per channel, breach, transfers."""
    t = tickets
    att = t[t["is_attendance"]]  # resolved/closed only

    rows = []
    for aid, ag in agents.set_index("agent_id").iterrows():
        my = att[att["agent_id"] == aid]
        valid = my[my["csat_valid"]]
        row = {
            "agent_id": aid,
            "display": f"{ag['name']} ({aid})",
            "name": ag["name"],
            "site": ag["site"],
            "team": ag["team"],
            "tier": int(ag["tier"]),
            "attendance": len(my),
            "csat_n": len(valid),
            "response_rate": _safe_div(len(valid), len(my)),
            "csat_mean": valid["csat_score"].mean() if len(valid) else np.nan,
            "share_le2": _safe_div(int(my["csat_le2"].sum()), len(valid)),
            "handle_median_min": my["handle_time_min"].median(),
            "handle_p90_min": my["handle_time_min"].quantile(0.90),
            "breach_rate": my["is_breach"].mean() if len(my) else np.nan,
            "days_to_resolve_median": my["handle_time_min"].median() / 1440.0,
        }
        for ch in CHANNELS:
            c = my[my["channel"] == ch]
            row[f"handle_median_{ch}"] = c["handle_time_min"].median()
            row[f"handle_p90_{ch}"] = c["handle_time_min"].quantile(0.90)
        # transfers: helpdesk only (column exists only in current system)
        hd = my[my["source_system"] == policy.HELPDESK_SOURCE]
        row["transfer_rate"] = (hd["transfers"] > 0).mean() if len(hd) else np.nan
        row["is_tier2"] = ag["team"] == policy.TIER2_TEAM
        rows.append(row)

    sc = pd.DataFrame(rows).sort_values("agent_id").reset_index(drop=True)
    return sc


def _safe_div(a: float, b: float) -> float:
    return a / b if b else np.nan
