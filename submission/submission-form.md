# Submission form — Vireo Audio support analytics

Every number below is read from an output file (`outputs/…`, `validation/results.md`) or a
`docs/…` log, not from memory. Only external facts are left as **[USER TO FILL]**: the Drive,
GitHub and recording links, the one-number and human hours, and the AI subscription cost.

## What did you build; the number and the money
A deterministic, one-command tool (`python -m vireo.run`) that produces a fair agent scorecard, a
defective-lot alert, and a static HTML report — plus a validation harness. **Headline:** the CSAT
dip is mostly **Pulse 2**, lots **PL2-2510/2511/2512** replacing at **38–43%** vs a **~7%** healthy
baseline (`outputs/money_summary.md`). **Money:** ≈ **689 excess units ≈ Rs 12.5 lakh** at the policy
cost **Rs 1,820/unit** — a floor (matched orders only). Remaining warranty exposure ≈ Rs 8.8 lakh.

## Cost per run; monthly at ~650 tickets/week
**Rs 0** per run — no paid model calls in the default path; all free-text handling is regex/keyword
(`src/vireo/textrules.py`). Volume ≈ 650×52/12 ≈ **2,817 tickets/month**. A per-ticket LLM
alternative would cost ≈ **Rs 5 × 2,817 = Rs 14,085/month**; we cost **Rs 0**. One-off labelling cost
actually incurred: **Rs 0** — sample labels were AI-drafted in-session (no external API call) and a
human verifies a spot-check subset; see `docs/ai_usage_log.md`.

## How do you know it works
Two things are validated and kept strictly separate (full detail + status tags: `validation/results.md`):
**(A)** an honest before/after of the text rule — **v1 (frozen)** vs **v2 (mined outside the sample)** —
on a **fresh 60-ticket held-out set** (`validation/test_set_to_label.csv`, seed 20261001, none of the
180 sample tickets) labelled by a **human**, with Wilson 95% intervals; **(B)** the older **180-ticket**
AI-drafted sample, kept only for context (the rule was tuned after Opus read it) and for the
human-vs-Opus agreement figure. The numbers below are written from `results.md` by
`validation/update_docs.py` — never hand-typed:

<!-- VALIDATION:START -->
**Validation (v1 vs v2).**

- Held-out test — HUMAN-LABELLED, n=60 (tickets Opus never read; predictor = text rule AND SKU VA-EB-PL2):
-   v1 (frozen): precision 100.0%, recall 54.1% [38.4%, 69.0%], F1 0.70
-   v2 (mined):  precision 100.0% [85.7%, 100.0%], recall 62.2% [46.1%, 75.9%], F1 0.77
-   Verdict: v2 improves recall (overlapping 95% intervals => within noise at this n).
- Historical 180-sample (context only, rule tuned after seeing it — NOT a test of v2): v1 precision 96.8%, recall 56.6% on n=180, human labels 49/180; human-vs-Opus agreement 30/40 = 75% on the blind subset.
- Failure kinds v2 targets: dead / one-sided bud and "only charges when wiggled/pressed" (typo-tolerant), mined outside the sample.
- Opus wrote BOTH rule versions and the AI-drafted labels on the 180 sample; the 60 held-out test labels are HUMAN. The rupee figure comes from replacement orders, not text, and does not change with the rule version.
<!-- VALIDATION:END -->

Lot alert fires on **exactly** PL2-2510/2511/2512 with **0 false alarms, 0 missed** — and does not
depend on the text rule (it is costed from replacement orders). Automated tests incl. a <1-min CLI
smoke (`pytest`).

## Did you change, narrow, or push back on the ask
Yes. (1) The "retrain the bottom ten" ask is confounded — a raw list blames the **Tier 2 warranty
team** (queue effect, policy §6). We deliver the bottom ten but caveat it and surface only **four**
"clear evidence" Chat agents to coach. (2) We lead with the **lot defect**, which the ask didn't
mention, because that's where the money is. (3) Finance's **Rs 2,500**/unit is wrong for Pulse 2;
policy gives **Rs 1,820** (off by Rs 680/unit).

## What is wrong with what we hand over
- The text rule has a real **recall gap**. On the fresh 60-ticket **human-labelled** held-out test,
  even the improved **v2 recall is 62.2%** (v1 54.1%) — it still **misses roughly four in ten** real
  Pulse-2 charging faults. Precision is 100% for both, and the 95% intervals overlap (v2's gain is
  3 tickets). It is a **corroborating** signal, not the costing basis.
- **Test-set composition caveat:** the 60 over-represent replacements (strata 30/15/15), so its error
  rates (v1 28.3%, v2 23.3%) are **not population error rates** — read recall, not error, off it.
- The 180-sample block is **context only**: labels there are AI-drafted by Opus and the rule was
  tuned after Opus read them, so it cannot test the rule (human-only recall was 43.5%, error 28.6%).
- The lot alert is validated **in-sample**; weeks-to-detect (~6) is a backtest, not a live trial.
- The rupee figure is **matched-orders only** (~35% of tickets have no `order_id`) → a **floor**.
- Open investigations, exactly as `outputs/data_quality_log.md` states: duplicates **none found**;
  junk IVR **27** (14 ASR-marker + 13 <=3-char messages), not ~40; legacy money units **no rescale**; refund+replacement breaches **6**;
  legacy-unit question treated as INR (no evidence to rescale).

## What did you leave out (and why)
Multi-page web app (a static file suffices); training-budget optimisation (no course prices in the
pack); Diwali top-five (out of scope); repeat-contact/FCR modelling (time cap); per-ticket LLM
(cost + determinism). Cut order followed the spec §7; nothing on the "never cut" list was cut.

## Anything nobody asked for
The **defective-lot alert** with a rupee number; **breach-credit** (Rs 3.72 lakh) and **transfer**
(Rs 3.71 lakh) costs shown to be flat and *not* the cause; the **6 refund+replacement** policy breaches.

## What did you use AI for
Default (shipped) path: **none** (Rs 0; deterministic regex/keyword rules). For **validation labels**,
a **human labelled 9 + 40 + 60 = 109 tickets** (9 seed + a 40-ticket blind subset of the 180 sample +
the fresh 60-ticket held-out test); **Opus drafted the other 171** labels of the 180 sample **blind to
the rule**. On the 40-ticket blind subset, human-vs-Opus **agreement was 30/40 = 75%** (`score.py`,
not invented; kinds in `docs/label_disagreements.md`). Opus also built the rule, so the 180-sample
figures are flagged as not independent — the 60-ticket test is the honest one. AI also assisted the
coding itself. **No external API was called; coding-assistant subscription cost: [USER TO FILL].**
Recording (prompts used, what changed, what was thrown away): **[USER TO FILL — recording link]**.

## Google Drive link (public: recording + memo + report)
**[USER TO FILL]**

## Monday hand-over (3 things)
1. **Rerun:** place the pack at `data/raw/`, then `python -m vireo.run` (see README); tests: `pytest`.
2. **The lot alert is the value; the ranking is context** — coach the four "clear evidence" agents, not a raw list.
3. **Open questions:** legacy money units, duplicate absence, and the QC confirmation for lots 2510/2511/2512.

## Honest hours
Logged in `docs/time_log.md`: **2:11 — Opus build time only** (not a substitute for the human's
hours). One number, ≤5h: **[USER TO FILL]**.
Human time (reading, prompting, labelling, review, recording): **[USER TO FILL]**.

## GitHub (public repo URL)
**[USER TO FILL]**
