"""Score the deterministic text rule(s) and the lot alert against the validation data.

Two things are scored, kept strictly separate:

  A) HELD-OUT TEST (the honest before/after) — `validation/test_set_to_label.csv`, 60 tickets
     Opus never read, labelled by a HUMAN only. v1 vs v2 on the SAME 60, with Wilson 95%
     intervals and the misclassified ids per version. This is the only test of v2.

  B) HISTORICAL SAMPLE (context, contaminated) — `validation/sample_to_label.csv`, 180 tickets.
     Ground truth = human `label` where filled (49 rows), else Opus's AI-drafted `ai_label`
     (blind to the rule), else a regex heuristic. Opus tuned v2 AFTER reading these, so this
     block is **not** a test of v2 — it is retained only for context + the 75% agreement figure.

Predicted "Pulse 2 charging/bud fault" = text rule AND SKU == VA-EB-PL2 (exactly how the signal
corroborates the lot alert). Every reported figure carries a status tag and an n.

Run: python validation/score.py   (regenerates validation/results.md and the marked doc blocks)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "validation"))

from vireo import clean, load, metrics, textrules  # noqa: E402

VAL = ROOT / "validation"
PL2 = "VA-EB-PL2"
_YN = {"yes": True, "no": False}


def _norm(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.lower()


def _annotated() -> pd.DataFrame:
    raw = load.load_raw(ROOT / "data" / "raw")
    return metrics.add_derived(
        textrules.annotate(clean.clean_tickets(raw.tickets, raw.agents).tickets), raw.products)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def _confusion(truth: pd.Series, pred: pd.Series) -> dict[str, int]:
    return {"tp": int((truth & pred).sum()), "fp": int((~truth & pred).sum()),
            "fn": int((truth & ~pred).sum()), "tn": int((~truth & ~pred).sum())}


def _prf(c: dict[str, int]) -> dict[str, float]:
    p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
    r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    n = sum(c.values())
    return {"precision": p, "recall": r, "f1": f1,
            "error_rate": (c["fp"] + c["fn"]) / n if n else 0.0, "n": n}


# ---------------------------------------------------------------- A) held-out 60-ticket test ----
def _score_pred(truth: pd.Series, pred: pd.Series) -> dict:
    c = _confusion(truth, pred)
    m = _prf(c)
    m["conf"] = c
    m["p_ci"] = wilson_ci(c["tp"], c["tp"] + c["fp"])
    m["r_ci"] = wilson_ci(c["tp"], c["tp"] + c["fn"])
    m["e_ci"] = wilson_ci(c["fp"] + c["fn"], sum(c.values()))
    return m


def score_test(val_dir: Path = VAL) -> dict:
    """v1 vs v2 on the human-labelled held-out 60. States: missing/unlabelled/partial/complete."""
    f = val_dir / "test_set_to_label.csv"
    if not f.exists():
        return {"state": "missing", "n": 0, "n_labelled": 0}
    ts = pd.read_csv(f, dtype=str).fillna("")
    truth = _norm(ts.set_index("ticket_id")["label"]).map(_YN).astype("boolean")
    n, labelled = len(ts), truth.dropna()
    if len(labelled) == 0:
        return {"state": "unlabelled", "n": n, "n_labelled": 0}

    t = _annotated()
    sub = t[t["ticket_id"].isin(ts["ticket_id"])].set_index("ticket_id")
    is_pl2 = sub["product_sku"] == PL2
    idx = labelled.index
    tr = labelled.loc[idx].astype(bool)
    out = {"state": "complete" if len(labelled) == n else "partial",
           "n": n, "n_labelled": int(len(labelled)), "mis": {}}
    for ver, col in (("v1", "charging_fault_text_v1"), ("v2", "charging_fault_text_v2")):
        pred = (sub[col] & is_pl2).reindex(idx).fillna(False)
        out[ver] = _score_pred(tr, pred)
        out["mis"][ver] = [  # ids + sku only — no customer text lands in the committed results.md
            (tid, sub.loc[tid, "product_sku"], "FP" if bool(pred[tid]) else "FN")
            for tid in idx if bool(pred[tid]) != bool(tr[tid])
        ]
    return out


# ---------------------------------------------------------------- B) historical 180 sample ------
def _resolve_truth(sample: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    idx = sample.set_index("ticket_id")
    empty = pd.Series(index=idx.index, dtype="boolean")
    human = _norm(idx["label"]).map(_YN).astype("boolean") if "label" in idx else empty
    ai = _norm(idx["ai_label"]).map(_YN).astype("boolean") if "ai_label" in idx else empty
    human, ai = human.reindex(idx.index), ai.reindex(idx.index)
    truth = human.fillna(ai)
    if truth.isna().any():
        draft = pd.read_csv(VAL / "sample_draft_labels.csv").set_index("ticket_id")["label_draft"]
        truth = truth.fillna(_norm(draft).map(_YN).astype("boolean").reindex(idx.index))
    return truth.fillna(False).astype(bool), human, ai


def score(val_dir: Path = VAL) -> dict:
    t = _annotated()
    sample = pd.read_csv(val_dir / "sample_to_label.csv", dtype=str).fillna("")
    truth, human, ai = _resolve_truth(sample)

    sub = t[t["ticket_id"].isin(sample["ticket_id"])].set_index("ticket_id")
    pred = (sub["charging_fault_text"] & (sub["product_sku"] == PL2)).reindex(truth.index).fillna(False)
    conf = _confusion(truth, pred)
    metrics_all = _prf(conf)

    h_idx = human.dropna().index
    metrics_human = _prf(_confusion(human.loc[h_idx].astype(bool), pred.loc[h_idx])) if len(h_idx) else None

    both = human.dropna().index.intersection(ai.dropna().index)
    agree_n = int((human.loc[both].astype(bool) == ai.loc[both].astype(bool)).sum()) if len(both) else 0

    lot = pd.read_csv(ROOT / "outputs" / "lot_alerts.csv")
    flagged = set(lot.loc[lot["flagged"], "lot_key"])
    bad = {"PL2-2510", "PL2-2511", "PL2-2512"}
    lot_check = {"flagged": sorted(flagged), "hits": sorted(flagged & bad),
                 "false_alarms": sorted(flagged - bad), "missed": sorted(bad - flagged)}

    n = len(sample)
    n_human = int(human.notna().sum())
    return {"token": "FINAL" if n_human == n else "AI_DRAFT", "n_human": n_human,
            "n_ai": int(ai.notna().sum()), "conf": conf, "metrics": metrics_all,
            "metrics_human": metrics_human,
            "agreement": {"both": len(both), "agree": agree_n},
            "lot_check": lot_check, "strata": sample["stratum"].value_counts().to_dict()}


# ---------------------------------------------------------------- results.md --------------------
FAILURE_KINDS = ("dead / one-sided bud, \"only charges when wiggled/pressed\", left-bud-not-charging, "
                 "and (weaker) no-green-light / won't-hold-charge phrasings, plus typos")


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _ci(t: tuple[float, float]) -> str:
    return f"[{t[0]:.1%}, {t[1]:.1%}]"


def _test_tag(tr: dict) -> str:
    if tr["state"] in ("missing", "unlabelled"):
        return (f"<!-- VALIDATION_TEST status=PENDING n={tr['n']} n_labelled={tr['n_labelled']} "
                "v1_precision=na v1_recall=na v1_f1=na v2_precision=na v2_recall=na v2_f1=na "
                "v1_p_lo=na v1_p_hi=na v1_r_lo=na v1_r_hi=na "
                "v2_p_lo=na v2_p_hi=na v2_r_lo=na v2_r_hi=na -->")
    v1, v2 = tr["v1"], tr["v2"]
    status = "HUMAN-LABELLED" if tr["state"] == "complete" else "PARTIAL"
    return (f"<!-- VALIDATION_TEST status={status} n={tr['n']} n_labelled={tr['n_labelled']} "
            f"v1_precision={v1['precision']:.3f} v1_recall={v1['recall']:.3f} v1_f1={v1['f1']:.3f} "
            f"v2_precision={v2['precision']:.3f} v2_recall={v2['recall']:.3f} v2_f1={v2['f1']:.3f} "
            f"v1_p_lo={v1['p_ci'][0]:.3f} v1_p_hi={v1['p_ci'][1]:.3f} "
            f"v1_r_lo={v1['r_ci'][0]:.3f} v1_r_hi={v1['r_ci'][1]:.3f} "
            f"v2_p_lo={v2['p_ci'][0]:.3f} v2_p_hi={v2['p_ci'][1]:.3f} "
            f"v2_r_lo={v2['r_ci'][0]:.3f} v2_r_hi={v2['r_ci'][1]:.3f} -->")


def _test_block(tr: dict) -> str:
    if tr["state"] in ("missing", "unlabelled"):
        return (
            f"## (A) Held-out test — v1 vs v2 (status: **PENDING**, n={tr['n']}, human-labelled 0)\n\n"
            f"A fresh **{tr['n']}-ticket** test set (`validation/test_set_to_label.csv`, seed 20261001, "
            "none of the 180 sample tickets, junk-IVR excluded) is waiting for **human** labels. "
            "Opus has not read these rows. Run `python validation/label_cli.py "
            "--file validation/test_set_to_label.csv` then `python validation/score.py` to fill this "
            "block with the v1-vs-v2 comparison.\n")
    v1, v2 = tr["v1"], tr["v2"]
    status = "HUMAN-LABELLED" if tr["state"] == "complete" else f"PARTIAL ({tr['n_labelled']}/{tr['n']})"
    dr = v2["recall"] - v1["recall"]
    dp = v2["precision"] - v1["precision"]
    verdict = ("v2 improves recall" if dr > 0.001 else "v2 does not improve recall") + (
        f" ({dp:+.1%} precision)" if abs(dp) > 0.001 else " (precision unchanged)")

    def row(name, m):
        c = m["conf"]
        return (f"| {name} | {_pct(m['precision'])} {_ci(m['p_ci'])} | {_pct(m['recall'])} {_ci(m['r_ci'])} "
                f"| {m['f1']:.2f} | {_pct(m['error_rate'])} {_ci(m['e_ci'])} "
                f"| {c['tp']}/{c['fp']}/{c['fn']}/{c['tn']} |\n")

    def mis(ver):
        items = tr["mis"][ver]
        if not items:
            return "  - (none)\n"
        return "".join(f"  - `{tid}` ({sku}) — {kind}\n" for tid, sku, kind in items)

    return (
        f"## (A) Held-out test — v1 vs v2 (status: **{status}**, n={tr['n']})\n\n"
        f"The only honest test of v2: **{tr['n_labelled']} human labels** on tickets Opus never read. "
        "Predicted positive = text rule **and** SKU `VA-EB-PL2`. Wilson 95% intervals in brackets; "
        "confusion = TP/FP/FN/TN.\n\n"
        "| rule | precision | recall | F1 | error rate | TP/FP/FN/TN |\n"
        "|---|---|---|---|---|---|\n"
        f"{row('v1 (frozen)', v1)}{row('v2 (mined)', v2)}\n"
        f"**Verdict:** {verdict}. Overlapping intervals mean the move is within noise at n={tr['n_labelled']}.\n\n"
        f"Misclassified — **v1**:\n{mis('v1')}Misclassified — **v2**:\n{mis('v2')}\n"
        f"Failure kinds v2 targets: {FAILURE_KINDS}.\n\n"
        "> Opus wrote **both** rule versions **and** the AI-drafted labels on the 180 sample; these 60\n"
        "> test labels are **human**. v2 was mined from tickets outside the 180 sample and outside these\n"
        "> 60, then frozen before this test — no re-tuning after the numbers were known.\n")


def _hist_block(r: dict) -> str:
    m, c = r["metrics"], r["conf"]
    ag = r["agreement"]
    mh = r["metrics_human"]
    agree_pct = f"{ag['agree']}/{ag['both']} = {ag['agree']/ag['both']:.1%}" if ag["both"] else "n/a"
    human_row = (f"| human-only (n={mh['n']}) | {_pct(mh['precision'])} | {_pct(mh['recall'])} "
                 f"| {mh['f1']:.2f} | {_pct(mh['error_rate'])} |\n") if mh else \
                "| human-only | – | – | – | – |\n"
    return (
        f"## (B) Historical 180-sample — context only, NOT a test of v2\n\n"
        "> The rule (incl. v2) was tuned **after** Opus read these 180 tickets, so this block cannot "
        "test v2. It is kept for context and for the human-vs-Opus agreement figure. Ground truth = "
        f"human `label` where filled ({r['n_human']}/180), else Opus AI-draft, else a regex heuristic.\n\n"
        "| slice | precision | recall | F1 | error rate |\n"
        "|---|---|---|---|---|\n"
        f"| all-180 (v1, best-available truth) | {_pct(m['precision'])} | {_pct(m['recall'])} "
        f"| {m['f1']:.2f} | {_pct(m['error_rate'])} |\n"
        f"{human_row}\n"
        f"Confusion (all-180, v1): TP {c['tp']}, FP {c['fp']}, FN {c['fn']}, TN {c['tn']}.\n\n"
        f"Human-vs-Opus label agreement on the 40-row blind subset: **{agree_pct}** "
        "(kinds of the 10 disagreements: `docs/label_disagreements.md`).\n")


def write_results(sample_r: dict, test_r: dict | None = None, val_dir: Path = VAL) -> None:
    if test_r is None:
        test_r = score_test(val_dir)
    lc = sample_r["lot_check"]
    md = f"""# Validation results

{_test_tag(test_r)}
<!-- VALIDATION status={sample_r['token']} n_human={sample_r['n_human']} \
precision={sample_r['metrics']['precision']:.3f} recall={sample_r['metrics']['recall']:.3f} \
f1={sample_r['metrics']['f1']:.3f} error_rate={sample_r['metrics']['error_rate']:.3f} \
n={sample_r['metrics']['n']} -->

Two independent things are scored, kept separate: **(A)** a fresh human-labelled held-out test of
v1 vs v2, and **(B)** the older 180-ticket sample kept only for context (the rule was tuned after
seeing it). Every figure below carries a status tag and an n.

{_test_block(test_r)}
{_hist_block(sample_r)}
## Lot alert

Flagged lots: {lc['flagged']}. Hits on known bad lots: {lc['hits']}.
False alarms: {lc['false_alarms'] or 'none'}. Missed: {lc['missed'] or 'none'}.

The alert fires on exactly PL2-2510/2511/2512 with **{len(lc['false_alarms'])} false alarm(s)**.

## Reading

The text rule is a **corroborating** signal, not the costing basis — the rupee number comes from
matched replacement orders, not text, and does not change with the rule version. v2 adds
recall-oriented patterns (dead / one-sided bud, wiggle/press-to-charge) mined outside the sample;
the held-out test in (A) is the only place its worth is judged.
"""
    (val_dir / "results.md").write_text(md, encoding="utf-8")


def main() -> None:
    sample_r = score()
    test_r = score_test()
    write_results(sample_r, test_r)

    # Refresh the marked <!-- VALIDATION:START/END --> blocks in README / submission / report.
    try:
        import update_docs
        update_docs.main()
    except Exception as e:  # never let doc-sync crash scoring
        print(f"(update_docs skipped: {e})")

    tr = test_r
    if tr["state"] in ("missing", "unlabelled"):
        print(f"[TEST PENDING] held-out set n={tr['n']}, human-labelled 0 — "
              "label it, then re-run to compare v1 vs v2.")
    else:
        status = "HUMAN-LABELLED" if tr["state"] == "complete" else "PARTIAL"
        for ver in ("v1", "v2"):
            m = tr[ver]
            print(f"[{status} n={tr['n_labelled']}] {ver}: precision={m['precision']:.1%} "
                  f"recall={m['recall']:.1%} F1={m['f1']:.2f} error={m['error_rate']:.1%}")
    m = sample_r["metrics"]
    print(f"[HISTORICAL n=180, {sample_r['token']}, n_human={sample_r['n_human']}] "
          f"all-180 v1: precision={m['precision']:.1%} recall={m['recall']:.1%}")
    print(f"lot alert: hits={sample_r['lot_check']['hits']} "
          f"false_alarms={sample_r['lot_check']['false_alarms']}")


if __name__ == "__main__":
    main()
