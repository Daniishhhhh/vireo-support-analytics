# Submission form — Vireo Audio support analytics

Every number below is read from an output file (`outputs/…`, `validation/results.md`) or a
`docs/…` log, not from memory.

## What did you build; the number and the money
A deterministic, one-command tool (`python -m vireo.run`) that produces a fair agent scorecard, a
defective-lot alert, and a static HTML report, plus a validation harness. **Headline:** the CSAT
dip is mostly **Pulse 2**, lots **PL2-2510/2511/2512** replacing at **38–43%** vs a **~7%** healthy
baseline (`outputs/lot_alerts.csv`, `outputs/money_summary.md`). **Money:** ≈ **689 excess units ≈
Rs 12.5 lakh** at the policy cost **Rs 1,820/unit**. This is a floor (see "What is wrong"). Remaining
warranty exposure on those lots ≈ Rs 8.8 lakh.

## Cost per run; monthly at ~650 tickets/week
**Rs 0** per run. There are no paid model calls in the default path; all free-text handling is
regex/keyword (`src/vireo/textrules.py`). Volume ≈ 650 × 52 / 12 ≈ **2,817 tickets/month**. A
per-ticket LLM alternative would cost ≈ **Rs 5 × 2,817 = Rs 14,085/month**; this tool costs **Rs 0**.
One-off labelling used no external API (labels were drafted inside the coding session and checked by
a human); see `docs/ai_usage_log.md`.

## How do you know it works
Two things are validated and kept strictly separate (full detail and status tags in
`validation/results.md`):

**(A) A before/after of the text rule on a fresh, human-labelled test set.** Rule **v1 (frozen)** vs
rule **v2 (mined outside the sample)**, scored on **60 tickets** that none of the earlier work had
read (`validation/test_set_to_label.csv`, seed 20261001, none of the 180 sample tickets). All 60
labels are human. Intervals are Wilson 95%.

**(B) The older 180-ticket sample**, kept only for context (the rule was tuned after Opus read it)
and for the human-vs-Opus agreement figure.

The numbers in the block below are written from `results.md` by `validation/update_docs.py`, never
hand-typed:

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

**How often it is wrong, in plain terms.** On the 60 human-labelled tickets the rule never raised a
false alarm (precision 100%), but it **missed about 4 in 10 real faults**: v1 caught about 54% and
v2 about 62%. On the first 49 human labels from the older sample the same kind of rule caught about
44% of real faults (error 28.6%). The two independent human checks agree, so ~25–30% error on this
kind of ticket is the honest figure. Kinds of case it gets wrong: battery-drain wording, "one of them
is just decoration", "never gets the green light in the case", single-side and typo or Hinglish
phrasings.

**Limits of these numbers.** (1) The 60-ticket test deliberately over-samples replacement tickets
(30 Pulse 2 with a replacement, 15 Pulse 2 without, 15 other products), so 28.3% and 23.3% are **not**
the error rate across all of Vireo's tickets. (2) v2's gain over v1 is about three more faults caught
and sits inside the overlapping intervals, so it is a small improvement, not a proven one. (3) The lot
alert (below) does not depend on this rule.

The lot alert fires on **exactly** PL2-2510/2511/2512 with **0 false alarms, 0 missed**, and it is
costed from replacement orders, not text. There are automated tests, including a CLI smoke test that
runs the whole pipeline in under a minute (`pytest`).

## Did you change, narrow, or push back on the ask
Yes.
1. The "retrain the bottom ten" ask is confounded. A raw list blames the **Tier 2 warranty team**,
   who get the escalated cases by design (queue effect, policy §6). We deliver the bottom ten because
   it was asked for, but caveat it, and we surface only **four** "clear evidence" Chat agents for
   coaching.
2. We lead with the **defective-lot finding**, which the ask never mentioned, because that is where
   the money is and it explains most of the CSAT dip.
3. Finance's **Rs 2,500** per replacement is wrong for Pulse 2. Policy gives unit cost plus Rs 340 =
   **Rs 1,820** (off by Rs 680 per unit).

## What is wrong with what we hand over
- **Text-rule quality.** The rule misses about 4 in 10 real faults (v1 recall 54.1%, v2 62.2% on 60
  human-labelled tickets; 43.5% on the earlier 49). It is a corroborating signal, not the costing
  basis.
- **Labels.** The 171 non-human labels in the 180 sample were drafted by Opus blind to the rule, but
  Opus also built the rule, so those figures are not independent. A blind check of 40 of them by a
  human agreed on **30 of 40 (75%)**. Nine of the ten disagreements are scope differences (the human
  labelled any hardware fault "yes", while the rule only fires on charging language); see
  `docs/label_disagreements.md`. Human labels always take priority in scoring.
- **Small samples.** 60 held-out tickets and 49 earlier human labels give wide intervals. v2's
  improvement is within noise.
- **Test-set composition.** The 60-ticket set is not a random sample of all tickets (see above).
- **Lot alert.** It is validated in-sample: I found those lots in this data, then built and tested the
  alert on the same data. The "about 6 weeks to detect" figure is a backtest, not a live trial.
- **Rupee figure.** It counts only replacements matched to an order, so it is a **floor**. About 35%
  of tickets have no `order_id`; a fallback match on customer and product covers 94.5% of tickets,
  but some matches are uncertain.
- **Open investigations, exactly as `outputs/data_quality_log.md` states them:** duplicate re-imports
  **none found**; junk phone transcripts **27 found** (14 with ASR markers, 13 of three characters or
  fewer), not the "about forty" the client mentioned, so some may be missed; legacy money units
  **no rescale** (ratios match the current system, treated as INR); refund plus replacement on the
  same ticket **6**.
- **Roster.** `agents.csv` has no shift or site history, so shift-level analysis is not possible.

## What did you leave out (and why)
A multi-page web app (a static report is enough and always runs); training-budget optimisation (no
course prices exist in the pack, so any split of the Rs 4 lakh would be invented); a Diwali top-five
ranking (the same fairness problems as the bottom ten, and it would reward easy queues);
repeat-contact/FCR modelling (needs an issue-matching rule the pack does not define, and time cap);
per-ticket LLM calls (cost and determinism). I followed the cut order in the spec; nothing on the
"never cut" list was cut.

## Anything nobody asked for
The **defective-lot alert** with a rupee number; the **breach-credit** (Rs 3.72 lakh) and
**transfer** (Rs 3.71 lakh) costs, shown to be flat and **not** the cause of the dip; the **6
refund-plus-replacement** policy breaches; and a name-protection step (public outputs show agent IDs
only, names only behind a flag into a gitignored folder).

## What did you use AI for
- **Shipped tool:** no AI at run time (Rs 0, deterministic rules).
- **Coding:** Claude Opus 4.8 in VS Code wrote the code, tests and documents in phases from a spec
  I prepared with Claude (Sonnet 5.5) in chat, which also profiled the data and wrote the prompts.
- **Where it helped:** fast profiling, finding the lot pattern, building the pipeline and tests, and
  catching bugs (for example a missing output folder on a clean run and a legacy timezone problem).
- **Where it wasted time or was wrong:** my first spec was far too big for a 5-hour cap and was
  rewritten; my early lot estimate (about Rs 9.7 lakh) was lower than the final because it used a
  weaker order match; the first rule scored well only against Opus's own labels, which a human check
  showed was too generous.
- **What was thrown away:** the six-page dashboard idea, the training-budget split, the first
  keyword patterns for "battery drain" and "no green light" (they did not hold up outside the
  sample), and any use of the AI-labelled 180 as a test for v2.
- **Human labelling:** I labelled 9 tickets, then 40 blind verification tickets, then the 60-ticket
  held-out test. Opus drafted the other 171 labels blind to the rule, and no external API was used.
- **Cost:** no external API spend. Coding-assistant subscription cost: approx. US$50 (Claude
  subscription used for the chat and for Opus in VS Code).
- **Recording (prompts used, what changed, what was thrown away):**
  https://drive.google.com/file/d/1AIB-Np2KVYbB3NK3yoWjmi-Ii-DUpVyI/view?usp=sharing

## Google Drive link (public: recording + memo + report)
https://drive.google.com/drive/folders/1flW6jD9pkFpn1gEC5DdiUc8CQNWqUfhW?usp=sharing

## Someone picks this up on Monday and you are unreachable: the three things they need to know
1. **Rerun:** place the data pack in `data/raw/`, then run `python -m vireo.run` (see the README);
   tests are `pytest`. Validation labels are in gitignored files; the README explains how to rebuild
   them.
2. **The lot alert is the value; the ranking is context.** Act on PL2-2510/2511/2512 first (ops/QC
   confirmation, inspect or hold remaining stock), and coach the four "clear evidence" agents, not a
   raw bottom-ten list.
3. **Open questions:** legacy money units, why fewer junk transcripts were found than expected, and
   the QC confirmation of the root cause for lots 2510–2512.

## Honest hours
- Opus build time (machine time only, from `docs/time_log.md`): **2:11 at the last log entry**;
  check the file for the final total. This overlaps with my own time below.
- My own time (reading the brief, working with Claude in chat, labelling 109 tickets, review, git,
  recording, Drive upload): included in the total below.
- **One number, total honest hours: 10**
- Over the 5-hour cap: the extra time went on a first spec that targeted the wrong scope (rewritten
  after the real brief arrived) and on extra validation (human labelling of 109 tickets and a
  held-out v1-vs-v2 test) so the error rate would be real rather than provisional.

## GitHub (public repo URL)
https://github.com/Daniishhhhh/vireo-support-analytics