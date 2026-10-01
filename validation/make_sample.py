"""Build a stratified validation sample (fixed seed). Writes:
  - sample_to_label.csv : ticket_id, channel, product_sku, customer_message, agent_notes, label
    (the `label` column is EMPTY for the human to fill; NO rule output is shown, to avoid bias)
  - sample_draft_labels.csv : ticket_id, label_draft from an independent, stricter heuristic
    (used only as a provisional stand-in until the human labels; see validation/results.md)

Label question (human ground truth): "Pulse 2 charging/bud fault: yes/no".
Run: python validation/make_sample.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vireo import clean, load, metrics, textrules  # noqa: E402

SEED = 20260929
STRATA_N = {
    "pulse2_replacement": 50,
    "other_replacement": 30,
    "pulse2_nonrepl": 40,
    "other": 40,
    "voice": 20,
}

# Independent, stricter heuristic for a PROVISIONAL Pulse-2 charging/bud-fault label.
# Deliberately broader than the production rule so the production rule's misses show up.
_GOLD = re.compile(
    r"(left|right|one)\s*(ear)?\s*bud|not\s*charg|won'?t\s*charge|no\s*charge|"
    r"not\s*taking\s*charge|0\s*%|zero\s*percent|green\s*light|no\s*led|dead|"
    r"drain|only\s*one\s*side|one\s*side|case.*charg|charg.*case|not\s*switching\s*on"
)


def gold_label(row: pd.Series) -> str:
    """Provisional label: Pulse-2 SKU AND charging/bud-fault language. Human overrides this."""
    if row["product_sku"] != "VA-EB-PL2":
        return "no"
    text = " ".join(str(x) for x in (row["customer_message"], row["agent_notes"])
                     if isinstance(x, str)).lower()
    return "yes" if _GOLD.search(text) else "no"


# Label columns that carry human/AI judgement — preserved across a re-generation of the
# real sample so re-running this script never destroys work already done.
_LABEL_COLS = ("label", "ai_label", "ai_reason", "label_source")


def main(out_dir: Path | None = None) -> None:
    raw = load.load_raw(ROOT / "data" / "raw")
    t = metrics.add_derived(textrules.annotate(clean.clean_tickets(raw.tickets, raw.agents).tickets),
                            raw.products)
    t = t[~t["is_junk_ivr"]]  # do not ask the human to label failed transcripts
    is_pl2 = t["product_sku"] == "VA-EB-PL2"
    is_repl = t["replacement_issued"] == "Y"
    pools = {
        "pulse2_replacement": t[is_pl2 & is_repl],
        "other_replacement": t[~is_pl2 & is_repl],
        "pulse2_nonrepl": t[is_pl2 & ~is_repl],
        "other": t[~is_pl2 & ~is_repl],
        "voice": t[t["channel"] == "voice"],
    }
    picks = []
    for name, n in STRATA_N.items():
        pool = pools[name]
        picks.append(pool.sample(min(n, len(pool)), random_state=SEED).assign(stratum=name))
    sample = pd.concat(picks).drop_duplicates("ticket_id").reset_index(drop=True)

    out = Path(out_dir) if out_dir else ROOT / "validation"
    out.mkdir(parents=True, exist_ok=True)
    is_real = out.resolve() == (ROOT / "validation").resolve()
    cols = ["ticket_id", "stratum", "channel", "product_sku", "customer_message", "agent_notes"]
    to_label = sample[cols].copy()
    to_label["label"] = ""  # human fills yes/no here

    target = out / "sample_to_label.csv"
    # Non-destructive on the real file: carry over any existing human/AI labels by ticket_id.
    if is_real and target.exists():
        prev = pd.read_csv(target, dtype=str).fillna("")
        keep = [c for c in _LABEL_COLS if c in prev.columns]
        to_label = to_label.drop(columns=[c for c in keep if c in to_label.columns]) \
            .merge(prev[["ticket_id"] + keep], on="ticket_id", how="left").fillna("")
    to_label.to_csv(target, index=False)

    draft = sample[["ticket_id"]].copy()
    draft["label_draft"] = sample.apply(gold_label, axis=1)
    draft.to_csv(out / "sample_draft_labels.csv", index=False)
    print(f"Wrote {len(sample)} tickets to {target} (strata: "
          f"{sample['stratum'].value_counts().to_dict()})")


if __name__ == "__main__":
    main()
