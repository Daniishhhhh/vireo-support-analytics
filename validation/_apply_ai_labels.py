"""Transcribe Opus's hand-read labels into sample_to_label.csv.

The judgements below were made by READING each ticket's customer_message +
agent_notes + product_sku (blind to textrules.py / charging_fault_text /
sample_draft_labels.csv / results.md). This script only writes them into the
CSV columns; it makes no labelling decision itself. See docs/ai_usage_log.md.

Rule applied by hand while reading: YES = a Pulse 2 (VA-EB-PL2) charging/power
hardware fault (bud not charging, dead bud, works only when wiggled in the
case, case not charging, battery won't hold charge). NO = everything else,
including any non-Pulse-2 product ("another product"), damage, delivery,
payment/coupon/invoice, app/firmware/pairing/connectivity with no hardware
fault, sound-quality only, and status/pre-sales queries with no fault stated.

The 9 human-labelled rows are left untouched (ai_label/ai_reason blank).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# The 9 pre-existing HUMAN ground-truth labels (ticket_id -> yes/no). Kept here (IDs only, no
# customer text) so they survive a fresh `make_sample.py` on a clean machine. These are final.
HUMAN: dict[str, str] = {
    "TK-245877": "no",  "TK-252245": "yes", "TK-248544": "yes",
    "TK-245748": "yes", "TK-247021": "yes", "TK-251468": "no",
    "TK-253228": "yes", "TK-248809": "yes", "TK-249244": "yes",
}

# ticket_id -> (ai_label, ai_reason<=8 words). Decided by reading, not by rule.
AI: dict[str, tuple[str, str]] = {
    "TK-249681": ("yes", "left bud not charging"),
    "TK-250165": ("yes", "left bud no green light in case"),
    "TK-252519": ("yes", "bud works only when wiggled in case"),
    "TK-250005": ("yes", "left bud not charging in case"),
    "TK-249322": ("no", "buzzing/static audio, sound quality"),
    "TK-252367": ("yes", "left bud not charging"),
    "TK-250995": ("no", "warranty status query, no fault"),
    "TK-250093": ("yes", "bud works only when wiggled in case"),
    "TK-252982": ("yes", "charging case not holding charge"),
    "TK-248199": ("no", "pod stays flat, no charge fault"),
    "TK-250157": ("yes", "left bud not charging"),
    "TK-251488": ("yes", "left bud not charging"),
    "TK-246347": ("yes", "bud only charges when pressed"),
    "TK-246591": ("yes", "left bud dead, not charging"),
    "TK-254156": ("yes", "battery wont hold charge"),
    "TK-248058": ("yes", "left bud dead, not charging"),
    "TK-249178": ("yes", "bud only charges when pressed"),
    "TK-246227": ("no", "damaged in transit"),
    "TK-248942": ("yes", "bud only charges when pressed"),
    "TK-253308": ("no", "wrong item shipped"),
    "TK-245887": ("yes", "left bud not charging"),
    "TK-252522": ("no", "random disconnects, connectivity"),
    "TK-251564": ("yes", "left bud wont hold charge"),
    "TK-247392": ("no", "pod stays flat, no charge fault"),
    "TK-248346": ("yes", "left bud not charging"),
    "TK-251967": ("yes", "left bud not charging"),
    "TK-248463": ("no", "RMA status query, no fault"),
    "TK-251904": ("yes", "left bud not charging"),
    "TK-251205": ("yes", "left bud not charging in case"),
    "TK-244007": ("no", "RMA status query, no fault"),
    "TK-251615": ("yes", "left bud not charging"),
    "TK-251818": ("yes", "left bud not charging in case"),
    "TK-250811": ("yes", "left bud not charging in case"),
    "TK-253904": ("yes", "left bud not charging in case"),
    "TK-252314": ("yes", "one bud dead, single-side audio"),
    "TK-248443": ("yes", "left bud not charging overnight"),
    "TK-251085": ("no", "reverse pickup pending"),
    "TK-246723": ("yes", "bud works only when wiggled in case"),
    "TK-252785": ("no", "RMA status query, no fault"),
    "TK-250813": ("yes", "left bud wont hold charge"),
    "TK-250375": ("yes", "left bud not charging in case"),
    # other_replacement stratum — all non-Pulse-2 products -> NO
    "TK-240401": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-243763": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-250807": ("no", "not Pulse 2 (AirLite)"),
    "TK-252640": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-242085": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-240421": ("no", "not Pulse 2 (AirLite)"),
    "TK-253783": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-240096": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-243939": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-242032": ("no", "not Pulse 2 (AirLite)"),
    "TK-242106": ("no", "not Pulse 2 (Strata 2)"),
    "TK-241478": ("no", "not Pulse 2 (AirLite)"),
    "TK-251875": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-241127": ("no", "not Pulse 2 (Nexa 1)"),
    "TK-242634": ("no", "not Pulse 2 (Strata 2)"),
    "TK-251611": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-253262": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-252592": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-248499": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-253740": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-252042": ("no", "not Pulse 2 (AirLite)"),
    "TK-253847": ("no", "not Pulse 2 (GaN charger)"),
    "TK-254559": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-245010": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-240535": ("no", "not Pulse 2 (AirLite)"),
    "TK-247073": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-240348": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-244798": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-242062": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-241380": ("no", "not Pulse 2 (Pulse 1)"),
    # pulse2_nonrepl stratum — Pulse 2 but no charging/power hardware fault
    "TK-251421": ("no", "app crash, no hardware fault"),
    "TK-251399": ("no", "firmware update issue"),
    "TK-248077": ("no", "delivery/tracking issue"),
    "TK-250436": ("no", "coupon/discount issue"),
    "TK-251594": ("no", "app issue, no hardware fault"),
    "TK-250372": ("no", "static audio, sound quality"),
    "TK-246526": ("no", "delivery delayed"),
    "TK-252912": ("no", "bluetooth dropouts, connectivity"),
    "TK-243340": ("no", "warranty status query"),
    "TK-250258": ("no", "warranty/RMA status query"),
    "TK-248668": ("no", "pairing failure, no hardware fault"),
    "TK-251897": ("no", "pre-sales compatibility query"),
    "TK-245666": ("no", "audio distortion, sound quality"),
    "TK-253992": ("no", "damaged in transit"),
    "TK-247800": ("no", "delivery address change"),
    "TK-248104": ("no", "invoice query"),
    "TK-252593": ("yes", "left bud not charging"),
    "TK-248208": ("no", "bluetooth dropouts, connectivity"),
    "TK-248616": ("no", "invoice/GST query"),
    "TK-250839": ("no", "OTP/login issue"),
    "TK-251229": ("yes", "left bud no charge in case"),
    "TK-248660": ("no", "payment/order issue"),
    "TK-252744": ("no", "crackling audio, sound quality"),
    "TK-251512": ("no", "refund delay"),
    "TK-246877": ("no", "promo/discount issue"),
    "TK-251317": ("yes", "battery drains fast, wont hold"),
    "TK-246776": ("no", "connectivity/range issue"),
    "TK-253116": ("no", "bluetooth dropouts, range"),
    "TK-250593": ("no", "mic issue, not charging"),
    "TK-252066": ("yes", "left bud not charging in case"),
    "TK-252300": ("no", "pairing issue"),
    "TK-248522": ("no", "pre-sales query"),
    "TK-250312": ("no", "delivery/tracking"),
    "TK-253565": ("yes", "battery drains fast, wont hold"),
    "TK-247739": ("no", "delivery address issue"),
    "TK-251646": ("no", "compatibility query"),
    "TK-246630": ("no", "refund pending"),
    "TK-248501": ("no", "delivery/tracking"),
    "TK-250027": ("no", "OTP/login issue"),
    "TK-245496": ("no", "repair status, no fault stated"),
    # other stratum — all non-Pulse-2 products -> NO
    "TK-241271": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-244562": ("no", "not Pulse 2 (Nexa 1)"),
    "TK-244386": ("no", "not Pulse 2 (Nexa 1)"),
    "TK-254046": ("no", "not Pulse 2 (AirLite)"),
    "TK-245120": ("no", "not Pulse 2 (charging case)"),
    "TK-245702": ("no", "not Pulse 2 (AirLite)"),
    "TK-246160": ("no", "not Pulse 2 (AirLite)"),
    "TK-249380": ("no", "not Pulse 2 (Strata 3)"),
    "TK-242925": ("no", "not Pulse 2 (Strata 2)"),
    "TK-243016": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-240056": ("no", "not Pulse 2 (Nexa 1)"),
    "TK-251722": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-247255": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-246098": ("no", "not Pulse 2 (Strata 3)"),
    "TK-245884": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-242995": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-247372": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-240953": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-245711": ("no", "not Pulse 2 (Strata 2)"),
    "TK-242473": ("no", "not Pulse 2 (Strata 2)"),
    "TK-240174": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-244437": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-245814": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-242137": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-254208": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-253225": ("no", "not Pulse 2 (AirLite)"),
    "TK-240799": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-252417": ("no", "not Pulse 2 (Arc neckband)"),
    "TK-243496": ("no", "not Pulse 2 (Strata 3)"),
    "TK-240163": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-252739": ("no", "not Pulse 2 (Nexa 1)"),
    "TK-247804": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-241336": ("no", "not Pulse 2 (AirLite)"),
    "TK-248164": ("no", "not Pulse 2 (Strata 3)"),
    "TK-244499": ("no", "not Pulse 2 (Pulse 1)"),
    "TK-241163": ("no", "not Pulse 2 (AirLite)"),
    "TK-245328": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-246546": ("no", "not Pulse 2 (charging case)"),
    "TK-242218": ("no", "not Pulse 2 (AirLite)"),
    "TK-249405": ("no", "not Pulse 2 (AirLite)"),
    # voice stratum
    "TK-242110": ("no", "not Pulse 2 (AirLite)"),
    "TK-252944": ("no", "not Pulse 2 (AirLite)"),
    "TK-254317": ("yes", "battery drains, wont hold charge"),
    "TK-248093": ("no", "not Pulse 2 (Strata 2)"),
    "TK-252137": ("no", "crackling audio, sound quality"),
    "TK-242461": ("no", "not Pulse 2 (Nexa Fit)"),
    "TK-251527": ("yes", "left bud not charging in case"),
    "TK-253752": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-240814": ("no", "not Pulse 2 (AirLite)"),
    "TK-253572": ("no", "damaged in transit"),
    "TK-246476": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-253191": ("no", "not Pulse 2 (Nexa 2)"),
    "TK-252023": ("no", "OTP/login issue"),
    "TK-252295": ("no", "not Pulse 2 (Orbit Mini)"),
    "TK-242044": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-248127": ("yes", "left bud not charging in case"),
    "TK-243700": ("no", "not Pulse 2 (Orbit speaker)"),
    "TK-248009": ("no", "payment/order issue"),
    "TK-244657": ("no", "pairing failure, no charging fault"),
    "TK-240409": ("no", "not Pulse 2 (Nexa 1)"),
}


def main() -> None:
    root = Path(__file__).resolve().parent
    csv = root / "sample_to_label.csv"
    df = pd.read_csv(csv, dtype=str).fillna("")

    for col in ("ai_label", "ai_reason", "label_source"):
        if col not in df.columns:
            df[col] = ""

    # 1) Human ground-truth rows (committed here so they survive a fresh make_sample on a
    #    clean machine — sample_to_label.csv itself is gitignored for customer privacy).
    for i, r in df.iterrows():
        if r["ticket_id"] in HUMAN:
            df.at[i, "label"] = HUMAN[r["ticket_id"]]
            df.at[i, "label_source"] = "human"
            df.at[i, "ai_label"] = ""
            df.at[i, "ai_reason"] = ""

    human_mask = df["ticket_id"].isin(HUMAN)
    unl = df[~human_mask]
    missing = [t for t in unl["ticket_id"] if t not in AI]
    extra = [t for t in AI if t not in set(unl["ticket_id"])]
    if missing or extra:
        raise SystemExit(f"mapping mismatch: missing={missing} extra={extra}")

    # 2) AI-drafted rows.
    for i, r in df[~human_mask].iterrows():
        lbl, why = AI[r["ticket_id"]]
        df.at[i, "ai_label"] = lbl
        df.at[i, "ai_reason"] = why
        df.at[i, "label_source"] = "ai_draft"

    df.to_csv(csv, index=False)
    n_h = int(human_mask.sum())
    n_ai = int((~human_mask).sum())
    n_yes = int((df.loc[~human_mask, "ai_label"] == "yes").sum())
    print(f"human rows: {n_h}")
    print(f"ai-drafted rows: {n_ai}  (yes={n_yes}, no={n_ai - n_yes})")
    print(f"columns: {list(df.columns)}")


if __name__ == "__main__":
    main()
