# Decisions Log

Format: decision — why — (spec/policy reference). Numbers I recompute go here when they
differ from `PROJECT_SPEC_v2.md` Section 1 (which is a hypothesis, not ground truth).

## Setup / data

- **`support-policy.pdf` is a genuine 2-page PDF, not a zip.** The brief said to unzip it to
  `data/raw/policy/`. The bytes are `%PDF-1.4`, `unzip` fails ("not a zipfile"). I did not
  fabricate a zip. Policy constants are taken from the brief's POLICY CONSTANTS block and
  encoded in `src/vireo/policy.py`. The original PDF is kept at `data/raw/support-policy.pdf`.
  No information lost — the brief already summarises the policy.

- **Row counts reconcile exactly** with the spec: tickets 11,750; orders 15,500;
  customers 9,500; agents 44; products 14. Asserted in `load.py`.

- **Roster has 44 rows, 44 unique agent_ids, all `to_date` blank** → one row per agent, no
  shift/site history (D15). Peer-group and shift analysis use the single roster row.

- **Two agents share one display name**: A3006 (Indore, Chat Frontline, tier 1) and A3029
  (Bengaluru, Logistics, tier 1). Join on `agent_id` only; display "agent_id" publicly. (D1, Sameer's email)

## Method decisions (recorded as I build; see also README §assumptions)

1. Handle time = first_response_at → resolved_at, per policy §10, split by channel.
2. CSAT on open/pending tickets: excluded (blank = no response, never zero). Policy.
3. Timezone: legacy `resolved_at` treated as UTC → +5:30; helpdesk left as displayed.
4. Order match: `order_id` first, fallback `customer_id + product_sku` (latest order on/before
   ticket creation); unmatched share reported.
5. Baseline lot rate = pooled rate of the same SKU's other lots.
6. Root cause worded "consistent with a manufacturing/QC fault; needs ops confirmation".
7. Replacement cost = unit_cost_inr + Rs 340 (policy §5). Pulse 2 = 1,480 + 340 = Rs 1,820.

## Phase 1 findings (recomputed)

- **Timezone fix verified**: 2,309 tickets had negative handle time before the fix (all legacy_fd);
  0 after +5h30m. Anchors match exactly: TK-240001 = 13 min, TK-240002 = 17 min.
- **Junk IVR = 27, not ~40.** Detection rule: `customer_message` contains an ASR-failure marker
  (`[inaudible]`, `[crosstalk]`, `[line dropped]`) **or** is <=3 characters (empty/"..."). Sameer
  estimated ~40; the rule finds **27** (14 with ASR markers + 13 with <=3-char messages). The
  remaining gap to ~40 is voice messages with typos/Hinglish ("helo", "jst decoraton", "kindly do the
  needful") that carry real intent, so flagging them as junk would wrongly discard real complaints.
  Decision: flag the 27; report the gap honestly rather than inflate to hit 40.
- **Duplicates: NONE FOUND.** Checked same customer+sku with created_at within +/-6h across
  legacy/helpdesk (covers the 5h30m offset), plus exact created_at and exact content. Zero pairs.
  No de-duplication applied.
- **Legacy money units: NO rescale.** refund/order_value ratio ~= 1.0 in both systems; legacy median
  refund ~2,250 vs helpdesk ~2,500 (same order of magnitude). No evidence of a 100x "native unit".
- **Open/pending = 567** (blank resolved_at), of which **249 carry a CSAT score** - excluded from both
  handle time and CSAT (not attendance).
- **Refund + replacement on same ticket = 6** (policy §5 prohibits): TK-240833, TK-244004, TK-245019,
  TK-247304, TK-250859, TK-253280.
- **Counts reconcile:** 11,183 attendance (resolved+closed) + 567 open/pending = 11,750.

## Phase 2 (recomputed)

- **Naive bottom ten** (lowest raw mean CSAT, all 44) = the six Tier 2 Escalations & Warranty
  agents (A3039-A3044, mean CSAT 2.44-2.86) + four Chat Frontline (A3004/A3005/A3007/A3006, ~2.96-3.03).
  This is the trap: a plain dashboard blames the warranty team who get the angriest customers by design.
- **Expected CSAT** = leave-one-agent-out cell mean over (channel x priority x family x assigned_team),
  with coarser fallbacks (channel x team, then team, then global) when a cell has <5 other-agent scores.
  Agent adjusted score = mean(actual - expected). Shrink toward 0 by n/(n+50). Bootstrap 95% CI, seed 20260929.
  Deliberately NOT using the bot `category` (unreliable; ~1,732 'Other').
- **Adjusted bottom ten**: five of six Tier 2 agents drop out; the stable signal is four Chat Frontline
  agents (A3004, A3005, A3007, A3006, all Chat Frontline) whose
  bootstrap CI excludes zero -> labelled "clear evidence". They stay in the bottom ten under raw,
  peer-group, adjusted, shrunk, AND after excluding Pulse 2 bad-lot tickets, so their low CSAT is not a
  Pulse 2 artefact. These four are the genuinely coachable cases.
- **The two shared-name agents diverge**: A3006 (Chat, mean 3.03) is "clear evidence"; A3029 (Logistics, 3.11)
  is "insufficient evidence". Joining on name would have merged a coaching case with a non-case.
- **Labels**: 4 clear evidence, 6 queue effect likely (all Tier 2), 34 insufficient evidence.
- Every rank is shown with n and a bootstrap interval. Tier 2 is never ranked on volume.

## Phase 3 (recomputed) — differs from spec §1, my computation stands

- **Flagged lots: PL2-2510, PL2-2511, PL2-2512** (Pulse 2), found by rule (Wilson 95% lower bound of
  the lot's replacement rate > pooled baseline of the SKU's other lots, min 100 orders). No lot names
  hard-coded. **Zero false alarms** across all other SKU-lot cells.
- **Replacement rate metric** = distinct matched orders with >=1 replacement ticket / orders in lot
  (deduped by order_ref so multiple contacts on one order count once). Rates: 2510 42.9%, 2511 43.4%,
  2512 38.3%; healthy baseline (non-flagged PL2 lots) 7.1%.
- **Difference from spec §1**: spec quoted ~33.5% (262 matched) and ~Rs 9.7 lakh / ~532 excess units,
  using **order_id-only** matching (~65% match). I add a **conservative customer+sku fallback** (order
  on/before the ticket, single unambiguous lot), lifting the match rate to **94.5%** (order_id 7,643;
  fallback 3,463; unmatched 644). With fuller matching + a healthy-lot baseline, I get **~689 excess
  units ≈ Rs 12.5 lakh (floor)**. Same story, larger magnitude. Trusting my computation per the brief.
- **Replacement cost per unit = Rs 1,820** (1,480 + 340), NOT Arjun's Rs 2,500 (off by Rs 680/unit).
- **Time-to-detect**: anchored on first shipment date (robust to 6 tickets dated before their order).
  Alarm fires **~6 / 7 / 8 weeks** after each lot started shipping (vs the ~7% norm).
- **Breach credits Rs 3.72 lakh (1,064 breaches), transfer cost Rs 3.71 lakh (1,215)** — match spec;
  breaches flat ~9%/month so NOT the cause.
- **Data quirk logged**: 6 tickets have created_at before their referenced order_date (ticket predates
  order). Left as-is; only affects a detection anchor, which I moved to first-shipment to be robust.
- **Text rule** flags 1,488 charging/bud-fault messages (typo-tolerant, junk-IVR excluded).

## Phase 4 (validation)

- **Sample = 180 tickets, stratified, fixed seed 20260929**: pulse2_replacement 50, pulse2_nonrepl
  40, other 40, other_replacement 30, voice 20 (deduped by ticket_id; junk-IVR excluded so the human
  never labels a failed transcript). `validation/sample_to_label.csv` shows ticket_id/stratum/channel/
  sku/message/notes and an **empty `label` column only — no rule output** (avoids anchoring the human).
- **Ground truth is the human `label` column.** Until it is filled, `score.py` falls back to an
  **independent regex heuristic** (`validation/sample_draft_labels.csv`, `make_sample._GOLD`),
  deliberately broader than the production rule, and marks every number PROVISIONAL. No LLM, Rs 0.
- **Validated predictor** = production `charging_fault_text` AND SKU `VA-EB-PL2` (exactly the signal
  that corroborates the lot alert), not the product-agnostic text flag alone.
- **Provisional scores** (vs heuristic draft, n=180): precision 96.8%, recall 85.7%, F1 0.91,
  **error rate 3.3%**. (Before the Phase-6 junk-IVR widening the sample scored 92.7% / 90.5% / 3.9%;
  excluding 13 more short transcripts shifted the sample.) Honest caveat: this is heuristic-vs-rule
  agreement, not human-validated; the
  final number goes in `validation/results.md` after the `label` column is filled and `score.py` re-run.
- **Lot alert on the sample**: fires on exactly PL2-2510/2511/2512, **0 false alarms, 0 missed**.
- **CLI smoke test** (`tests/test_validation.py`) runs the whole pipeline into a temp dir in <1 min and
  asserts report.html + lot_alerts.csv exist. Fixed `run.main` to `mkdir` the out dir before writing
  the DQ log (previously relied on `outputs/` pre-existing; failed on a clean target).

## Phase 5 (report, docs, public-repo hygiene)

- **Public-repo hygiene.** The repo and Drive folder are public, so committed outputs carry
  **agent_id + team only** — never names. `run._anon` replaces the `display` name with the
  agent_id and drops `name`/`site` from every public CSV and from `report.html`. Names appear
  only under the opt-in `--with-names` flag, written to `outputs/private/*_named.csv` +
  `report_named.html`, which is **gitignored**. `.gitignore` also excludes `data/raw/`,
  `data/processed/`, and `validation/sample_to_label.csv` (customer free text). The README tells
  the reader where to drop the data pack. Coaching still works: labels + intervals are on the
  public tables; a manager maps agent_id→name once, privately.
- **Validation status tag.** `score.py` writes a machine-readable `<!-- VALIDATION status=... -->`
  line into `results.md`; the report/README/memo/form all quote that one source and show
  **PROVISIONAL** (heuristic draft) until the human `label` column is filled, then **FINAL**.

## Phase 7 — AI-drafted validation labels + blind human check

- **Opus drafted the 171 not-yet-human-labelled rows, blind to the rule.** I read each ticket's
  `customer_message` + `agent_notes` + `product_sku` only. I did **not** run `textrules.py` /
  `charging_fault_text`, did not open `sample_draft_labels.csv` or `results.md`, and used no
  regex/script to decide. `validation/_apply_ai_labels.py` only transcribes the judgements
  (ticket_id → `ai_label` y/n + `ai_reason` ≤8 words). New columns: `ai_label`, `ai_reason`,
  `label_source` (human/ai_draft). The **9 human labels are unchanged** and left with blank `ai_label`.
- **Label rule applied by hand:** YES = a **Pulse 2 (VA-EB-PL2)** charging/power hardware fault (bud
  not charging, dead bud, works only when wiggled in the case, case not charging, battery won't hold
  charge). NO = any non-Pulse-2 product ("another product"), damage, delivery, payment/coupon/invoice,
  app/firmware/pairing/connectivity with no hardware fault, sound-quality-only, and status/pre-sales
  queries with no fault stated. Borderline "pod won't seat/stays flat" → NO (not a charge fault).
  Result: **38 yes / 133 no** across the 171.
- **Independence caveat (stated everywhere):** Opus also built the rule, so the all-180 figures are
  **not fully independent**. The trustworthy check is the human-verified subset.
- **Blind human verification:** `validation/verify_ids.txt` = **40 tickets** drawn from the 171
  (fixed seed **20260930**, none among the 9 human rows). `label_cli.py --subset verify` shows only
  those 40, **hides `ai_label`**, and writes the human `label`. The human labels the 40; I do not.
- **`score.py` reworked:** ground truth = human `label` if filled, else `ai_label`, else the regex
  heuristic (fallback only). Reports (a) all-180, (b) human-only, (c) human-vs-AI agreement +
  disagreement list. Status token **AI_DRAFT** (with `n_human`) until all 180 are human-labelled,
  then **FINAL**. The agreement % comes from `score.py`, not invented.
- **Current numbers (AI_DRAFT, n_human=9):** all-180 precision **100%**, recall **68.9%**, F1 **0.82**,
  error **7.8%** (TP 31 / FP 0 / FN 14 / TN 135). The 14 FNs are genuine faults the keyword rule
  misses — battery-drain, "works only when wiggled", single-side/"just decoration", "no green light".
  This is a real **recall gap**, documented, not a labelling error; the rule stays a *corroborating*
  signal for the lot alert (which is costed from replacement orders, not text). Human-only (n=9):
  precision 100%, recall 85.7%.
- **Privacy + reproducibility:** `sample_to_label.csv` stays gitignored (customer free text). The
  labels are reproducible on a clean machine from committed, text-free files: `_apply_ai_labels.py`
  (AI dict + the 9 HUMAN labels, IDs only) and `verify_ids.txt`. Test suite kept green (29) by
  pointing sample-regeneration tests at tmp dirs and making `make_sample.main()` non-destructive
  (preserves existing labels on the real file). No external API; Rs 0 marginal.

## Phase 8 — rule v2 + honest held-out test

- **v1 frozen, v2 exposed.** `flag_text_v1` / `charging_fault_text_v1` keep the original behaviour
  (asserted in `tests/test_textrules_v2.py`). `flag_text_v2` = v1 **OR** the mined groups, so
  recall(v2) ≥ recall(v1) by construction. Production `charging_fault_text` stays bound to **v1**,
  so the money and lot outputs — which never read it anyway — are provably unchanged (hash test).
- **v2 mined aggregate-only, outside the 180 sample AND the 60 test set.** `validation/mine_v2.py`
  compares phrase frequencies in the bad-lot Pulse 2 replacement corpus (811 tickets, lots
  PL2-2510/2511/2512) vs the non-replacement Pulse 2 baseline (3,165), printing/writing **only
  aggregate counts** (no ticket text), so the 60 test tickets stay unread even though they are also
  excluded. Only groups with real positive bad-lot lift ship:
  - `dead_or_one_sided` — 8.9% bad vs 2.6% base (**+6.3%**)
  - `wiggle_or_press` — 3.7% bad vs 0.3% base (**+3.4%**)
- **Thrown away by the mining** (documented in `rule_v2_patterns.md`, not shipped): no-green-light /
  no-LED (**0** hits in the bad-lot corpus — that phrasing lived in the 180 sample, excluded here);
  won't-hold-charge / battery-drain (**negative** lift — matches battery-life questions on the
  healthy baseline, would cost precision); Hinglish charge-negation (**0** hits). Data over the
  spec's guessed list.
- **Fresh test set, unread.** `make_test_set.py` draws **60** tickets (seed **20261001**), excludes
  all 180 sample ids (from `_apply_ai_labels.HUMAN+AI`) and junk-IVR, strata 30 PL2-repl / 15
  PL2-nonrepl / 15 other. Writes `test_set_to_label.csv` (gitignored; ticket_id, sku, message,
  notes, empty label — **no rule/AI columns**) + `test_ids.txt` (committed, IDs only). Opus did not
  read/print/label any row.
- **Scoring & docs.** `score.py` scores v1 vs v2 on the 60 with **Wilson 95% intervals**, confusion
  and misclassified ids (id+sku only, no text), handling pending/partial/complete. The 180 sample is
  kept as a **clearly-marked historical block** ("rule tuned after seeing these; NOT a test of v2").
  Every figure carries a status tag + n. `update_docs.py` rewrites only the `<!-- VALIDATION:START/
  END -->` blocks in README/submission/report.html from `results.md`. **No re-tuning after the test**
  — the held-out result is pending human labels; no v2 verdict is claimed yet.

<!-- APPEND-DECISIONS -->
