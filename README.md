# Vireo Audio — Support Analytics

A small, deterministic tool that answers the real question behind "CSAT is sliding, which agents do
we retrain?" It builds a **fair agent scorecard**, a **defective-lot alert with a rupee number**, and
a **validation harness** — from the raw support export, on a clean machine, with **one command** and
**zero paid model calls**.

**Headline:** the CSAT dip is mostly one product (Pulse 2, lots PL2-2510/2511/2512 at ~38–43%
replacement vs a ~7% baseline), not the agents. Excess cost ≈ **Rs 12.5 lakh** (a floor, policy cost
Rs 1,820/unit). See `memo/memo_to_priya.md` and `outputs/report.html`.

## What it produces (`outputs/`)

| File | What |
|---|---|
| `report.html` | One static page (no server/CDN): headline, monthly CSAT with/without Pulse 2, lot alert, naive vs fair bottom ten, data-quality. |
| `money_summary.md` | Excess units, rupee cost, match rate, remaining exposure, breach/transfer cost. |
| `lot_alerts.csv` | Per SKU-lot replacement rate, Wilson bound, flag, weeks-to-detect. |
| `agent_scorecard.csv` | One row per agent (agent_id + team only), CSAT/handle/breach + adjusted score, interval, label. |
| `bottom_ten_naive.csv` / `bottom_ten_adjusted.csv` | The trap list vs the fair list. |
| `ranking_stability.csv` | Each flagged agent across five ranking methods. |
| `data_quality_log.md` | Every fix/exclusion with row count + example ids. |

Public outputs carry **agent_id + team only**. Names are written only with `--with-names`, to the
gitignored `outputs/private/`.

## Clean-machine setup

Requires **Python 3.11+**.

```bash
# 1. Place the data pack (not committed) at data/raw/ :
#    tickets.csv orders.csv customers.csv agents.csv products.csv
#    (plus email-thread.txt, README.txt, support-policy.pdf, PROJECT_SPEC_v2.md at repo root)
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash; use bin/activate on macOS/Linux
pip install -r requirements.txt
```

## Run (one command)

```bash
python -m vireo.run --data data/raw --out outputs --processed data/processed
```

Deterministic (fixed seed 20260929); regenerates every file above in ~15s. Add `--with-names` for the
private, name-bearing copies.

## Tests

```bash
pytest            # 29 tests: data traps, fair ranking, lot alert, validation, CLI smoke (<1 min)
```

## Human labelling step — for the FINAL validation number

The sample labels are **AI-drafted** (Opus read each ticket blind to the rule; see
`docs/ai_usage_log.md`). Because Opus also built the rule, the all-180 figures are **not fully
independent** — the trustworthy check is the human-verified block in `validation/results.md`. A
40-ticket blind subset (`validation/verify_ids.txt`, seed 20260930) is waiting for a human:

```bash
# On a fresh clone, rebuild the labelled sample first (sample_to_label.csv is gitignored —
# it holds customer text; the labels themselves live in text-free committed files):
python validation/make_sample.py        # regenerate the 180-row sample from your data pack
python validation/_apply_ai_labels.py    # write the 9 human + 171 AI-drafted labels (IDs only)

python validation/label_cli.py --subset verify   # 40 blind-check rows; ai_label hidden; y/n/s/u/q; autosaves
python validation/score.py                        # rewrites results.md; reports human-vs-AI agreement
```

To go fully FINAL, label all 180 (`python validation/label_cli.py`) then re-run `score.py`.
`results.md` tags status **AI_DRAFT** vs **FINAL** in a machine-readable line; report/memo/form quote that one file.

## Rule v2 — honest before/after on a held-out test

`charging_fault_text_v1` (the original text rule) is **frozen**; **v2** adds two pattern groups
(dead / one-sided bud, "only charges when wiggled/pressed") mined from tickets **outside** the 180
sample and the 60-ticket test — corpus counts in `validation/rule_v2_patterns.md`. To judge v2
fairly (Opus already read all 180 sample tickets, so they can't test a rule Opus then tuned), a
**fresh 60-ticket set Opus never read** is labelled by a human, then v1 and v2 are scored on the
same 60 with Wilson 95% intervals:

```bash
python validation/make_test_set.py     # 60 tickets (seed 20261001); gitignored, IDs in test_ids.txt
python validation/label_cli.py --file validation/test_set_to_label.csv   # human labels; rule output hidden
python validation/score.py              # scores v1 vs v2 + refreshes results.md and the block below
```

The money and lot outputs never read the text rule, so switching versions cannot move the rupee
number (`tests/` assert the output hashes are unchanged). Current status (auto-written from
`validation/results.md`):

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

## Decisions (decide, write down, explain — full log in `docs/decisions.md`)

1. Handle time per policy §10, split by channel.
2. CSAT on open/pending tickets excluded (blank ≠ zero).
3. Legacy `resolved_at` treated as UTC → **+5:30**; helpdesk left as displayed. (Verified: TK-240001=13min, TK-240002=17min.)
4. Order match: `order_id` first, then a conservative `customer_id + sku` fallback (order on/before ticket, single lot); unmatched share reported (**94.5%** matched).
5. Baseline lot rate = pooled other lots of the same SKU; money uses the **healthy** (non-flagged) baseline ~7%.
6. Root cause worded **"consistent with a manufacturing/QC fault; needs ops confirmation"** — not proven.
7. Replacement cost = unit cost + Rs 340 → Pulse 2 = **Rs 1,820** (not Finance's Rs 2,500).
8. Join agents on **agent_id only** — two agents share one display name (A3006 Chat/Indore and A3029 Logistics/Bengaluru), so a name join would wrongly merge them.

## Known limitations

- Validation labels are **AI-drafted** (Opus, blind to the rule) with a human verifying a 40-ticket
  subset; all-180 figures are not fully independent (Opus also built the rule). See `results.md`.
- The lot alert is validated **in-sample**; treat weeks-to-detect as a backtest, not a live trial.
- The rupee figure is a **floor** — matched orders only (~35% of tickets have no order_id).
- The text rule is deterministic and typo-tolerant but will **miss some voice/Hinglish** phrasings.
- Junk-IVR detection flags 27 failed transcripts (14 ASR-marker + 13 messages of ≤3 chars; not Sameer's ~40 estimate — the gap is real typo/Hinglish voice text); duplicates: none found; no legacy money rescale — all recorded in `docs/decisions.md` and `outputs/data_quality_log.md`.
