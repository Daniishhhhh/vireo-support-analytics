"""Tiny labelling helper. NO rule output and NO AI label are ever shown (avoid bias).

Shows customer_message + agent_notes for each unlabelled ticket and asks: charging/bud fault?
Keys:  y = yes,  n = no,  s = skip (leave blank),  u = undo last,  q = save & quit.
Autosaves the CSV after every keypress.

Run: python validation/label_cli.py                                   # the 180 sample, every blank row
     python validation/label_cli.py --subset verify                  # only the 40 blind-check rows
     python validation/label_cli.py --file validation/test_set_to_label.csv  # the 60 held-out test
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
VERIFY = HERE / "verify_ids.txt"
_HIDDEN = ("ai_label", "ai_reason", "label_source")  # never display these


def _arg(flag: str) -> str | None:
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def main() -> None:
    file_arg = _arg("--file")
    csv = Path(file_arg) if file_arg else HERE / "sample_to_label.csv"
    verify_only = "--subset" in sys.argv and "verify" in sys.argv

    df = pd.read_csv(csv, dtype=str)
    if "label" not in df.columns:
        df["label"] = ""
    df["label"] = df["label"].fillna("")
    blank = df["label"].str.strip() == ""

    if verify_only:
        ids = set(VERIFY.read_text().split())
        order = df.index[blank & df["ticket_id"].isin(ids)].tolist()
        print(f"VERIFY subset: {len(order)} of {len(ids)} blind-check rows still blank.")
    else:
        order = df.index[blank].tolist()

    sku_col = "product_sku" if "product_sku" in df.columns else ("sku" if "sku" in df.columns else None)
    print(f"{len(order)} unlabelled of {len(df)} in {csv.name}. y/n/s(kip)/u(ndo)/q(uit). "
          "Question: does the free text show a Pulse 2 charging/bud fault?")

    history: list[int] = []
    i = 0
    while i < len(order):
        idx = order[i]
        r = df.loc[idx]
        tag = f" ({r[sku_col]})" if sku_col else ""
        print(f"\n[{i+1}/{len(order)}] {r['ticket_id']}{tag}")
        print(f"  msg  : {str(r.get('customer_message', ''))[:300]}")
        print(f"  notes: {str(r.get('agent_notes', ''))[:200]}")
        ans = input("  > ").strip().lower()
        if ans == "q":
            break
        if ans == "u" and history:
            i = history.pop()
            continue
        if ans in ("y", "n"):
            df.loc[idx, "label"] = "yes" if ans == "y" else "no"
        elif ans != "s":
            print("  (use y/n/s/u/q)"); continue
        df.to_csv(csv, index=False)
        history.append(i)
        i += 1

    df.to_csv(csv, index=False)
    left = int((df["label"].str.strip() == "").sum())
    print(f"\nSaved {csv.name}. {left} still blank. Re-run `python validation/score.py` when done.")


if __name__ == "__main__":
    main()
