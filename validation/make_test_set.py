"""Build a FRESH, held-out test set of 60 tickets to judge rule v2 honestly.

Why a new set: Opus has already read the text of all 180 tickets in
`sample_to_label.csv`, so that sample is contaminated for testing a rule Opus
then tuned. These 60 are drawn from tickets Opus has NOT read and are labelled
by a human only. No rule output and no AI label are written here.

Exclusions: the 180 sample ids (from _apply_ai_labels.HUMAN + AI, committed and
text-free) and junk-IVR rows. Stratified, fixed seed 20261001:
  30 Pulse 2 (VA-EB-PL2) with replacement_issued = Y
  15 Pulse 2 without replacement
  15 non-Pulse-2

Writes:
  - validation/test_set_to_label.csv  (gitignored: customer free text) — columns
    ticket_id, sku, customer_message, agent_notes, label(empty). NOTHING else.
  - validation/test_ids.txt           (committed, IDs only) — the 60 ticket ids,
    so the set is reproducible and mine_v2.py can hold it out.

After writing, DO NOT read/print/label any row: the point is an unread test set.
Run: python validation/make_test_set.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "validation"))

from vireo import clean, load, metrics, textrules  # noqa: E402
from _apply_ai_labels import AI, HUMAN  # noqa: E402  (180 sample ids, IDs only)

SEED = 20261001
STRATA_N = {"pulse2_replacement": 30, "pulse2_nonrepl": 15, "other": 15}


def build() -> pd.DataFrame:
    raw = load.load_raw(ROOT / "data" / "raw")
    t = metrics.add_derived(
        textrules.annotate(clean.clean_tickets(raw.tickets, raw.agents).tickets),
        raw.products,
    )
    sample_ids = set(HUMAN) | set(AI)  # the 180 already-read tickets
    t = t[~t["ticket_id"].isin(sample_ids)]  # never reuse a read ticket
    t = t[~t["is_junk_ivr"]]                 # never ask the human to label a failed transcript

    is_pl2 = t["product_sku"] == "VA-EB-PL2"
    is_repl = t["replacement_issued"] == "Y"
    pools = {
        "pulse2_replacement": t[is_pl2 & is_repl],
        "pulse2_nonrepl": t[is_pl2 & ~is_repl],
        "other": t[~is_pl2],
    }
    picks = []
    for name, n in STRATA_N.items():
        pool = pools[name]
        if len(pool) < n:
            raise SystemExit(f"stratum {name}: only {len(pool)} available, need {n}")
        picks.append(pool.sample(n, random_state=SEED).assign(stratum=name))
    return pd.concat(picks).drop_duplicates("ticket_id").reset_index(drop=True)


def main() -> None:
    sample = build()
    out = ROOT / "validation"
    # test_set_to_label.csv: ticket_id, sku, message, notes, empty label. No rule/AI columns.
    to_label = sample[["ticket_id", "product_sku", "customer_message", "agent_notes"]].copy()
    to_label = to_label.rename(columns={"product_sku": "sku"})
    to_label["label"] = ""  # human fills yes/no
    to_label.to_csv(out / "test_set_to_label.csv", index=False)

    # test_ids.txt: committed, IDs only (reproducible + lets mine_v2 hold the set out).
    (out / "test_ids.txt").write_text(
        "\n".join(sorted(sample["ticket_id"])) + "\n", encoding="utf-8"
    )
    # Print counts ONLY — never the ticket text (keep the test set unread).
    n_pl2 = int((sample["product_sku"] == "VA-EB-PL2").sum())
    print(f"Wrote {len(sample)} tickets to {out / 'test_set_to_label.csv'} (gitignored).")
    print(f"Strata: {sample['stratum'].value_counts().to_dict()}")
    print(f"SKU split: PL2={n_pl2}, other={len(sample) - n_pl2}")
    print(f"Wrote {len(sample)} ids to {out / 'test_ids.txt'} (committed, IDs only).")


if __name__ == "__main__":
    main()
