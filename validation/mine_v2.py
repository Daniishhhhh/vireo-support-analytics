"""Mine v2 pattern groups from tickets OUTSIDE the 180 sample and the 60 test set.

This produces ONLY aggregate phrase-frequency counts — it never prints or writes an
individual ticket's text — so the held-out 60 stay unread even though they are also
excluded from the corpus here. Corpus split (Pulse 2 / VA-EB-PL2 only):
  - bad-lot   : tickets matched to a flagged lot (PL2-2510/2511/2512) with replacement_issued=Y
  - baseline  : Pulse 2 tickets with replacement_issued != Y (healthy contacts)

For each v2 pattern group (imported from vireo.textrules, so the doc describes exactly the
shipped rule) it reports how many bad-lot vs baseline tickets the group matches, and the lift.
It also lists the top discriminative unigrams/bigrams as evidence. Writes
validation/rule_v2_patterns.md.

Run: python validation/mine_v2.py
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "validation"))

from vireo import clean, load, lots, metrics, textrules  # noqa: E402
from _apply_ai_labels import AI, HUMAN  # noqa: E402

BAD_LOTS = {"PL2-2510", "PL2-2511", "PL2-2512"}
_TOKEN = re.compile(r"[a-z']+")
_STOP = set("the a an and or but to of in on for with is are was it my me i we you they this that "
            "not no so as at be been being have has had do does did will would can could my our "
            "your their there here he she them his her its please pls hi hello team thanks thank "
            "regards sir madam am pm ok okay".split())


def _corpora() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    raw = load.load_raw(ROOT / "data" / "raw")
    t = metrics.add_derived(
        textrules.annotate(clean.clean_tickets(raw.tickets, raw.agents).tickets), raw.products)
    matched = lots.match_orders(t, raw.orders)  # gives lot_key per ticket
    t = t.merge(matched[["ticket_id", "lot_key"]], on="ticket_id", how="left")

    held_out = set(HUMAN) | set(AI) | set(
        (ROOT / "validation" / "test_ids.txt").read_text().split())
    t = t[~t["ticket_id"].isin(held_out)]
    t = t[~t["is_junk_ivr"] & (t["product_sku"] == "VA-EB-PL2")]

    bad = t[(t["lot_key"].isin(BAD_LOTS)) & (t["replacement_issued"] == "Y")]
    base = t[t["replacement_issued"] != "Y"]
    to_pairs = lambda d: list(zip(d["customer_message"], d["agent_notes"]))  # noqa: E731
    return to_pairs(bad), to_pairs(base)


def _ngrams(pairs: list[tuple[str, str]]) -> Counter:
    """Per-document presence counts of uni/bigrams (each n-gram counted once per ticket)."""
    c: Counter = Counter()
    for m, n in pairs:
        text = " ".join(str(x) for x in (m, n) if isinstance(x, str)).lower()
        toks = [w for w in _TOKEN.findall(text) if w not in _STOP and len(w) > 2]
        seen = set(toks)
        seen |= {f"{a} {b}" for a, b in zip(toks, toks[1:])}
        c.update(seen)
    return c


def _discriminative(bad: Counter, base: Counter, n_bad: int, n_base: int, top: int = 25):
    rows = []
    for g, kb in bad.items():
        if kb < 5:
            continue
        rb = kb / n_bad
        rbase = base.get(g, 0) / n_base if n_base else 0.0
        rows.append((g, kb, base.get(g, 0), rb, rbase, rb - rbase))
    rows.sort(key=lambda r: r[5], reverse=True)
    return rows[:top]


def _group_counts(pairs: list[tuple[str, str]]) -> dict[str, int]:
    counts = {k: 0 for k in textrules.V2_GROUPS}
    for m, n in pairs:
        for k, hit in textrules.v2_group_hits(m, n).items():
            counts[k] += int(hit)
    return counts


def main() -> None:
    bad, base = _corpora()
    nb, nx = len(bad), len(base)
    gb, gx = _group_counts(bad), _group_counts(base)
    v1_bad = sum(textrules.flag_text_v1(m, n) for m, n in bad)
    v2_bad = sum(textrules.flag_text_v2(m, n) for m, n in bad)
    disc = _discriminative(_ngrams(bad), _ngrams(base), nb, nx)

    lines = [
        "# Rule v2 — mined pattern groups (corpus counts)",
        "",
        "Mined from Pulse 2 (VA-EB-PL2) tickets **outside** the 180-ticket sample **and** the 60-ticket",
        f"held-out test set (both excluded). Only aggregate counts are shown — no ticket text is printed",
        "or stored here, so the 60 test tickets stay unread. Source: `validation/mine_v2.py`, which",
        "imports the exact regexes shipped in `vireo.textrules.V2_GROUPS`.",
        "",
        f"- **bad-lot corpus** (lots {sorted(BAD_LOTS)}, replacement_issued=Y): **{nb}** tickets",
        f"- **baseline corpus** (Pulse 2, non-replacement): **{nx}** tickets",
        f"- v1 catches **{v1_bad}/{nb} = {v1_bad/nb:.1%}** of the bad-lot corpus; "
        f"v2 catches **{v2_bad}/{nb} = {v2_bad/nb:.1%}** (v2 = v1 OR the groups below).",
        "",
        "## Pattern groups and why each is included",
        "",
        "Each group targets a Pulse-2 charging/power/dead-bud failure kind. `bad %` is the share of",
        "the bad-lot corpus a group matches, `base %` the share of the healthy baseline; a group earns",
        "its place when it fires materially more on bad-lot tickets (lift > 0) — i.e. it points at the",
        "defect, not at generic support chatter. The predictor is always `group AND SKU==VA-EB-PL2`.",
        "",
        "| group | bad-lot hits | bad % | baseline hits | base % | lift |",
        "|---|---|---|---|---|---|",
    ]
    for k in textrules.V2_GROUPS:
        rb = gb[k] / nb if nb else 0
        rx = gx[k] / nx if nx else 0
        lines.append(f"| `{k}` | {gb[k]} | {rb:.1%} | {gx[k]} | {rx:.1%} | {rb - rx:+.1%} |")

    lines += [
        "",
        "Shipped groups (positive bad-lot lift): `dead_or_one_sided` (one bud dead / \"just a",
        "decoration\" / stopped working) and `wiggle_or_press` (only charges/works when wiggled,",
        "pressed or held in the case). Both are typo-tolerant (charg/chrg/charing/cahrg/...).",
        "",
        "**Thrown away by the mining** (documented, not shipped):",
        "- *no-green-light / no-LED*: 0 hits in the 811-ticket bad-lot corpus — the \"never gets the",
        "  green light\" phrasing lived in the 180 sample (excluded here); a broad form also matched",
        "  pairing chatter. A 0-support pattern earns no place.",
        "- *won't-hold-charge / battery-drain*: negative lift (fires more on the healthy baseline —",
        "  battery-life questions — than on bad-lot tickets); it would cost precision for ~no recall.",
        "- *Hinglish charge-negation* (\"charge nahi\", \"kaam nahi\"): 0 hits in the corpus; not added.",
        "",
        "## Top discriminative phrases (uni/bigrams, per-ticket presence)",
        "",
        "Evidence the groups above track real bad-lot language. Each row: phrase, bad-lot ticket count,",
        "baseline count, and the rate difference (bad − baseline). Aggregate only.",
        "",
        "| phrase | bad-lot | baseline | lift |",
        "|---|---|---|---|",
    ]
    for g, kb, kbase, rb, rbase, lift in disc:
        lines.append(f"| `{g}` | {kb} | {kbase} | {lift:+.1%} |")
    lines += [
        "",
        "> Built without reading any ticket in the 180 sample or the 60-ticket test set. v2 fires",
        "> wherever v1 fires, so recall(v2) ≥ recall(v1) by construction; whether the added recall",
        "> costs precision is decided only on the held-out 60 (see `validation/results.md`).",
        "",
    ]
    (ROOT / "validation" / "rule_v2_patterns.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"bad-lot corpus n={nb}, baseline n={nx}")
    print(f"v1 recall-on-bad {v1_bad}/{nb}={v1_bad/nb:.1%}  v2 recall-on-bad {v2_bad}/{nb}={v2_bad/nb:.1%}")
    for k in textrules.V2_GROUPS:
        print(f"  {k:18s} bad {gb[k]:4d} ({gb[k]/nb:5.1%})  base {gx[k]:4d} ({gx[k]/nx:5.1%})")
    print("wrote validation/rule_v2_patterns.md")


if __name__ == "__main__":
    main()
