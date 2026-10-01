# Rule v2 — mined pattern groups (corpus counts)

Mined from Pulse 2 (VA-EB-PL2) tickets **outside** the 180-ticket sample **and** the 60-ticket
held-out test set (both excluded). Only aggregate counts are shown — no ticket text is printed
or stored here, so the 60 test tickets stay unread. Source: `validation/mine_v2.py`, which
imports the exact regexes shipped in `vireo.textrules.V2_GROUPS`.

- **bad-lot corpus** (lots ['PL2-2510', 'PL2-2511', 'PL2-2512'], replacement_issued=Y): **811** tickets
- **baseline corpus** (Pulse 2, non-replacement): **3165** tickets
- v1 catches **584/811 = 72.0%** of the bad-lot corpus; v2 catches **616/811 = 76.0%** (v2 = v1 OR the groups below).

## Pattern groups and why each is included

Each group targets a Pulse-2 charging/power/dead-bud failure kind. `bad %` is the share of
the bad-lot corpus a group matches, `base %` the share of the healthy baseline; a group earns
its place when it fires materially more on bad-lot tickets (lift > 0) — i.e. it points at the
defect, not at generic support chatter. The predictor is always `group AND SKU==VA-EB-PL2`.

| group | bad-lot hits | bad % | baseline hits | base % | lift |
|---|---|---|---|---|---|
| `dead_or_one_sided` | 72 | 8.9% | 82 | 2.6% | +6.3% |
| `wiggle_or_press` | 30 | 3.7% | 10 | 0.3% | +3.4% |

Shipped groups (positive bad-lot lift): `dead_or_one_sided` (one bud dead / "just a
decoration" / stopped working) and `wiggle_or_press` (only charges/works when wiggled,
pressed or held in the case). Both are typo-tolerant (charg/chrg/charing/cahrg/...).

**Thrown away by the mining** (documented, not shipped):
- *no-green-light / no-LED*: 0 hits in the 811-ticket bad-lot corpus — the "never gets the
  green light" phrasing lived in the 180 sample (excluded here); a broad form also matched
  pairing chatter. A 0-support pattern earns no place.
- *won't-hold-charge / battery-drain*: negative lift (fires more on the healthy baseline —
  battery-life questions — than on bad-lot tickets); it would cost precision for ~no recall.
- *Hinglish charge-negation* ("charge nahi", "kaam nahi"): 0 hits in the corpus; not added.

## Top discriminative phrases (uni/bigrams, per-ticket presence)

Evidence the groups above track real bad-lot language. Each row: phrase, bad-lot ticket count,
baseline count, and the rate difference (bad − baseline). Aggregate only.

| phrase | bad-lot | baseline | lift |
|---|---|---|---|
| `left` | 633 | 371 | +66.3% |
| `case` | 497 | 383 | +49.2% |
| `bud` | 384 | 260 | +39.1% |
| `replacement` | 414 | 465 | +36.4% |
| `charge` | 326 | 262 | +31.9% |
| `one` | 321 | 248 | +31.7% |
| `charging` | 314 | 225 | +31.6% |
| `dispatched` | 272 | 76 | +31.1% |
| `earbud` | 272 | 177 | +27.9% |
| `left earbud` | 258 | 157 | +26.9% |
| `left one` | 181 | 79 | +19.8% |
| `left bud` | 189 | 126 | +19.3% |
| `side` | 190 | 146 | +18.8% |
| `doa` | 145 | 0 | +17.9% |
| `bud case` | 150 | 24 | +17.7% |
| `arranged` | 145 | 11 | +17.5% |
| `under doa` | 142 | 0 | +17.5% |
| `under` | 142 | 0 | +17.5% |
| `right` | 169 | 109 | +17.4% |
| `new` | 141 | 0 | +17.4% |
| `approved reverse` | 139 | 0 | +17.1% |
| `rma shared` | 138 | 0 | +17.0% |
| `rma` | 143 | 41 | +16.3% |
| `taking` | 150 | 90 | +15.7% |
| `approved` | 155 | 112 | +15.6% |

> Built without reading any ticket in the 180 sample or the 60-ticket test set. v2 fires
> wherever v1 fires, so recall(v2) ≥ recall(v1) by construction; whether the added recall
> costs precision is decided only on the held-out 60 (see `validation/results.md`).

