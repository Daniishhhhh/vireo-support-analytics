"""CLI entry: python -m vireo.run --data data/raw --out outputs

Runs the full pipeline: load → clean → scorecard/ranking → lot alert → report.
Deterministic (fixed seeds). Writes all outputs and processed tables.
"""
from __future__ import annotations

import argparse
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from . import clean, load

# Columns that could identify a real person — stripped from every PUBLIC output.
_NAME_COLS = ("name", "site")


def _anon(df: pd.DataFrame) -> pd.DataFrame:
    """Public view: show agent_id + team only. Replace display name with the id, drop name/site."""
    df = df.copy()
    if "display" in df.columns and "agent_id" in df.columns:
        df["display"] = df["agent_id"]
    drop = [c for c in _NAME_COLS if c in df.columns]
    return df.drop(columns=drop) if drop else df


def build_clean(data_dir: str, processed_dir: str, out_dir: str) -> clean.CleanResult:
    """Phase 1: load, clean, write DQ log, save processed tables."""
    raw = load.load_raw(data_dir)
    result = clean.clean_tickets(raw.tickets, raw.agents)

    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    result.tickets.to_parquet(Path(processed_dir) / "tickets_clean.parquet") \
        if _has_parquet() else \
        result.tickets.to_csv(Path(processed_dir) / "tickets_clean.csv", index=False)
    clean.write_dq_log(result.dq, Path(out_dir) / "data_quality_log.md", len(raw.tickets))
    return result


def _has_parquet() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Vireo support analytics pipeline")
    ap.add_argument("--data", default="data/raw")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--processed", default="data/processed")
    ap.add_argument("--with-names", action="store_true",
                    help="also write name-bearing tables to outputs/private/ (gitignored)")
    args = ap.parse_args(argv)

    t0 = time.time()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    raw = load.load_raw(args.data)
    cr = clean.clean_tickets(raw.tickets, raw.agents)
    clean.write_dq_log(cr.dq, Path(args.out) / "data_quality_log.md", len(raw.tickets))

    # Later phases (imported lazily so Phase-1 works standalone).
    from . import lots, metrics, ranking, report, textrules

    tickets = textrules.annotate(cr.tickets)
    tickets = metrics.add_derived(tickets, raw.products)
    Path(args.processed).mkdir(parents=True, exist_ok=True)
    tickets.to_csv(Path(args.processed) / "tickets_clean.csv", index=False)

    scorecard = metrics.agent_scorecard(tickets, raw.agents)
    lot = lots.build_lot_analysis(tickets, raw.orders, raw.products)
    rank = ranking.build_rankings(
        tickets, raw.agents, scorecard, badlot_ticket_ids=lot.badlot_ticket_ids
    )

    out = Path(args.out)
    # PUBLIC outputs: agent_id + team only, never names (repo/Drive are public).
    pub = replace(rank, scorecard=_anon(rank.scorecard), naive=_anon(rank.naive),
                  adjusted=_anon(rank.adjusted), stability=_anon(rank.stability))
    pub.scorecard.to_csv(out / "agent_scorecard.csv", index=False)
    pub.naive.to_csv(out / "bottom_ten_naive.csv", index=False)
    pub.adjusted.to_csv(out / "bottom_ten_adjusted.csv", index=False)
    pub.stability.to_csv(out / "ranking_stability.csv", index=False)
    lot.alerts.to_csv(out / "lot_alerts.csv", index=False)
    lot.cost_by_quarter.to_csv(out / "replacement_cost_by_quarter.csv", index=False)
    (out / "money_summary.md").write_text(lot.money_summary_md, encoding="utf-8")
    report.write_report(out / "report.html", tickets, raw, pub, lot)

    if args.with_names:  # private, gitignored: the only place names appear
        priv = out / "private"
        priv.mkdir(parents=True, exist_ok=True)
        rank.scorecard.to_csv(priv / "agent_scorecard_named.csv", index=False)
        rank.naive.to_csv(priv / "bottom_ten_naive_named.csv", index=False)
        rank.adjusted.to_csv(priv / "bottom_ten_adjusted_named.csv", index=False)
        rank.stability.to_csv(priv / "ranking_stability_named.csv", index=False)
        report.write_report(priv / "report_named.html", tickets, raw, rank, lot)
        print(f"  (wrote name-bearing tables to {priv}/ - gitignored)")

    print(f"Done in {time.time() - t0:.1f}s. Outputs in {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
