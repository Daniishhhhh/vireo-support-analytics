"""Fair ranking: case-mix-adjusted expected CSAT, shrinkage, bootstrap intervals.

Naive bottom ten = lowest raw mean CSAT (what a plain dashboard shows). Adjusted bottom ten
uses expected CSAT per ticket (leave-one-agent-out cell mean over
channel x priority x family x assigned_team), shrinks small-n agents toward zero, and adds a
bootstrap interval. Tier 2 stays in its own peer group and is labelled 'queue effect likely'.
Deterministic: fixed RNG seed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import policy

SEED = 20260929
SHRINK_K = 50          # small-n agents pulled toward zero
MIN_PEER = 5           # min other-agent tickets in a cell for leave-one-out
BOOT_ITERS = 1000
STRATA = ["channel", "priority", "family", "assigned_team"]


@dataclass
class Rankings:
    scorecard: pd.DataFrame     # scorecard + adjusted columns + labels
    naive: pd.DataFrame         # bottom ten, raw
    adjusted: pd.DataFrame      # bottom ten, adjusted+shrunk (published)
    stability: pd.DataFrame     # sensitivity across methods


def _expected_csat(v: pd.DataFrame) -> pd.Series:
    """Leave-one-agent-out expected CSAT per ticket, with coarser fallbacks."""
    exp = pd.Series(np.nan, index=v.index)
    for keys in (STRATA, ["channel", "assigned_team"], ["assigned_team"]):
        cell_sum = v.groupby(keys)["csat_score"].transform("sum")
        cell_n = v.groupby(keys)["csat_score"].transform("count")
        ag_sum = v.groupby(keys + ["agent_id"])["csat_score"].transform("sum")
        ag_n = v.groupby(keys + ["agent_id"])["csat_score"].transform("count")
        denom = cell_n - ag_n
        loo = (cell_sum - ag_sum) / denom.where(denom >= MIN_PEER)
        exp = exp.fillna(loo)
    return exp.fillna(v["csat_score"].mean())  # global fallback


def _bootstrap_ci(diffs: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    if len(diffs) < 2:
        return (np.nan, np.nan)
    idx = rng.integers(0, len(diffs), size=(BOOT_ITERS, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def _adjusted_by_agent(v: pd.DataFrame) -> pd.DataFrame:
    """Per-agent adjusted score (mean actual-expected), shrunk, with bootstrap CI + mean expected."""
    rng = np.random.default_rng(SEED)
    out = []
    for aid, g in v.groupby("agent_id"):
        diffs = g["diff"].to_numpy()
        n = len(diffs)
        adj = float(diffs.mean())
        lo, hi = _bootstrap_ci(diffs, rng)
        out.append({
            "agent_id": aid,
            "adj_score": adj,
            "adj_shrunk": adj * n / (n + SHRINK_K),
            "adj_ci_lo": lo,
            "adj_ci_hi": hi,
            "mean_expected": float(g["expected"].mean()),
        })
    return pd.DataFrame(out)


def _peer_group(row: pd.Series) -> str:
    if row["team"] == policy.TIER2_TEAM:
        return f"T2:{row['team']}"
    return f"T1:{row['team']}"


def build_rankings(
    tickets: pd.DataFrame,
    agents: pd.DataFrame,
    scorecard: pd.DataFrame,
    badlot_ticket_ids: set[str] | None = None,
) -> Rankings:
    """Compute naive and adjusted bottom-ten lists plus a sensitivity/stability table."""
    badlot_ticket_ids = badlot_ticket_ids or set()
    v = tickets[tickets["csat_valid"]].copy()
    v["expected"] = _expected_csat(v)
    v["diff"] = v["csat_score"] - v["expected"]

    adj = _adjusted_by_agent(v)
    sc = scorecard.merge(adj, on="agent_id", how="left")
    sc["peer_group"] = sc.apply(_peer_group, axis=1)

    # peer-relative raw CSAT (agent mean minus ticket-level peer-group mean)
    peer_mean = v.merge(agents[["agent_id", "team", "tier"]], on="agent_id")
    peer_mean["peer_group"] = peer_mean.apply(
        lambda r: f"T2:{r['team']}" if r["team"] == policy.TIER2_TEAM else f"T1:{r['team']}", axis=1
    )
    pm = peer_mean.groupby("peer_group")["csat_score"].mean()
    sc["peer_mean_csat"] = sc["peer_group"].map(pm)
    sc["csat_vs_peer"] = sc["csat_mean"] - sc["peer_mean_csat"]

    # method (e): adjusted score excluding Pulse 2 bad-lot tickets
    v_excl = v[~v["ticket_id"].isin(badlot_ticket_ids)]
    adj_excl = v_excl.groupby("agent_id")["diff"].mean().rename("adj_excl_badlots")
    sc = sc.merge(adj_excl, on="agent_id", how="left")

    scored = sc[sc["csat_n"] > 0]
    b = {
        "raw": _bottom10(scored, "csat_mean"),
        "peer": _bottom10(scored, "csat_vs_peer"),
        "adjusted": _bottom10(scored, "adj_score"),
        "adjusted_shrunk": _bottom10(scored, "adj_shrunk"),
        "adj_excl_badlots": _bottom10(scored, "adj_excl_badlots"),
    }
    for name, ids in b.items():
        sc[f"in_bottom10_{name}"] = sc["agent_id"].isin(ids)

    sc["label"] = sc.apply(lambda r: _label(r, v["csat_score"].mean()), axis=1)

    naive = sc[sc["in_bottom10_raw"]].sort_values("csat_mean")
    adjusted = sc[sc["in_bottom10_adjusted_shrunk"]].sort_values("adj_shrunk")

    in_any = sc["in_bottom10_raw"] | sc["in_bottom10_adjusted_shrunk"]
    stab_cols = ["agent_id", "display", "team", "tier", "csat_n", "csat_mean",
                 "adj_score", "adj_shrunk", "adj_ci_lo", "adj_ci_hi", "label"] + \
                [f"in_bottom10_{n}" for n in b]
    stability = sc.loc[in_any, stab_cols].sort_values("csat_mean")

    return Rankings(sc, _slim(naive), _slim(adjusted), stability)


def _bottom10(df: pd.DataFrame, col: str) -> set[str]:
    return set(df.nsmallest(10, col)["agent_id"])


def _label(row: pd.Series, global_mean: float) -> str:
    """clear evidence / insufficient evidence / queue effect likely."""
    if row["csat_n"] == 0:
        return "no CSAT data"
    hard_queue = row["is_tier2"] or (row["mean_expected"] < global_mean - 0.20)
    if hard_queue:
        return "queue effect likely"
    if row["csat_n"] >= 30 and row["adj_ci_hi"] < 0:
        return "clear evidence"
    return "insufficient evidence"


def _slim(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["agent_id", "display", "team", "tier", "csat_n", "response_rate", "csat_mean",
            "share_le2", "handle_median_min", "adj_score", "adj_shrunk",
            "adj_ci_lo", "adj_ci_hi", "label"]
    return df[cols].reset_index(drop=True)
