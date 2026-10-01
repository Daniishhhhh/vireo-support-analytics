# Validation results

<!-- VALIDATION_TEST status=HUMAN-LABELLED n=60 n_labelled=60 v1_precision=1.000 v1_recall=0.541 v1_f1=0.702 v2_precision=1.000 v2_recall=0.622 v2_f1=0.767 v1_p_lo=0.839 v1_p_hi=1.000 v1_r_lo=0.384 v1_r_hi=0.690 v2_p_lo=0.857 v2_p_hi=1.000 v2_r_lo=0.461 v2_r_hi=0.759 -->
<!-- VALIDATION status=AI_DRAFT n_human=49 precision=0.968 recall=0.566 f1=0.714 error_rate=0.133 n=180 -->

Two independent things are scored, kept separate: **(A)** a fresh human-labelled held-out test of
v1 vs v2, and **(B)** the older 180-ticket sample kept only for context (the rule was tuned after
seeing it). Every figure below carries a status tag and an n.

## (A) Held-out test — v1 vs v2 (status: **HUMAN-LABELLED**, n=60)

The only honest test of v2: **60 human labels** on tickets Opus never read. Predicted positive = text rule **and** SKU `VA-EB-PL2`. Wilson 95% intervals in brackets; confusion = TP/FP/FN/TN.

| rule | precision | recall | F1 | error rate | TP/FP/FN/TN |
|---|---|---|---|---|---|
| v1 (frozen) | 100.0% [83.9%, 100.0%] | 54.1% [38.4%, 69.0%] | 0.70 | 28.3% [18.5%, 40.8%] | 20/0/17/23 |
| v2 (mined) | 100.0% [85.7%, 100.0%] | 62.2% [46.1%, 75.9%] | 0.77 | 23.3% [14.4%, 35.4%] | 23/0/14/23 |

**Verdict:** v2 improves recall (precision unchanged). Overlapping intervals mean the move is within noise at n=60.

Misclassified — **v1**:
  - `TK-253448` (VA-EB-PL2) — FN
  - `TK-251735` (VA-EB-PL2) — FN
  - `TK-244129` (VA-EB-PL2) — FN
  - `TK-251796` (VA-EB-PL2) — FN
  - `TK-249487` (VA-EB-PL2) — FN
  - `TK-247069` (VA-EB-PL2) — FN
  - `TK-248895` (VA-EB-PL2) — FN
  - `TK-251501` (VA-EB-PL2) — FN
  - `TK-248599` (VA-EB-PL2) — FN
  - `TK-249197` (VA-EB-PL2) — FN
  - `TK-250770` (VA-EB-PL2) — FN
  - `TK-254246` (VA-EB-PL2) — FN
  - `TK-244767` (VA-EB-PL2) — FN
  - `TK-246157` (VA-EB-PL2) — FN
  - `TK-248202` (VA-EB-PL1) — FN
  - `TK-242165` (VA-SW-NX2) — FN
  - `TK-245005` (VA-EB-AIR) — FN
Misclassified — **v2**:
  - `TK-253448` (VA-EB-PL2) — FN
  - `TK-251735` (VA-EB-PL2) — FN
  - `TK-249487` (VA-EB-PL2) — FN
  - `TK-247069` (VA-EB-PL2) — FN
  - `TK-248895` (VA-EB-PL2) — FN
  - `TK-251501` (VA-EB-PL2) — FN
  - `TK-249197` (VA-EB-PL2) — FN
  - `TK-250770` (VA-EB-PL2) — FN
  - `TK-254246` (VA-EB-PL2) — FN
  - `TK-244767` (VA-EB-PL2) — FN
  - `TK-246157` (VA-EB-PL2) — FN
  - `TK-248202` (VA-EB-PL1) — FN
  - `TK-242165` (VA-SW-NX2) — FN
  - `TK-245005` (VA-EB-AIR) — FN

Failure kinds v2 targets: dead / one-sided bud, "only charges when wiggled/pressed", left-bud-not-charging, and (weaker) no-green-light / won't-hold-charge phrasings, plus typos.

> Opus wrote **both** rule versions **and** the AI-drafted labels on the 180 sample; these 60
> test labels are **human**. v2 was mined from tickets outside the 180 sample and outside these
> 60, then frozen before this test — no re-tuning after the numbers were known.

## (B) Historical 180-sample — context only, NOT a test of v2

> The rule (incl. v2) was tuned **after** Opus read these 180 tickets, so this block cannot test v2. It is kept for context and for the human-vs-Opus agreement figure. Ground truth = human `label` where filled (49/180), else Opus AI-draft, else a regex heuristic.

| slice | precision | recall | F1 | error rate |
|---|---|---|---|---|
| all-180 (v1, best-available truth) | 96.8% | 56.6% | 0.71 | 13.3% |
| human-only (n=49) | 90.9% | 43.5% | 0.59 | 28.6% |

Confusion (all-180, v1): TP 30, FP 1, FN 23, TN 126.

Human-vs-Opus label agreement on the 40-row blind subset: **30/40 = 75.0%** (kinds of the 10 disagreements: `docs/label_disagreements.md`).

## Lot alert

Flagged lots: ['PL2-2510', 'PL2-2511', 'PL2-2512']. Hits on known bad lots: ['PL2-2510', 'PL2-2511', 'PL2-2512'].
False alarms: none. Missed: none.

The alert fires on exactly PL2-2510/2511/2512 with **0 false alarm(s)**.

## Reading

The text rule is a **corroborating** signal, not the costing basis — the rupee number comes from
matched replacement orders, not text, and does not change with the rule version. v2 adds
recall-oriented patterns (dead / one-sided bud, wiggle/press-to-charge) mined outside the sample;
the held-out test in (A) is the only place its worth is judged.
