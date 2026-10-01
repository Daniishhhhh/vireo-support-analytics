# Time Log — Vireo Support Build

Real timestamps, IST. Effort cap ~5 hours (enforced). One number reported at the end.

| Phase | Start | End | Elapsed | Notes |
|---|---|---|---|---|
| 0 — Read pack, scope, skeleton | 2026-09-29 15:54 | 16:00 | 0:06 | Read spec/emails/README, created repo, verified row counts |
| 1 — Load, clean, DQ log | 2026-09-29 16:00 | 16:08 | 0:08 | policy/load/clean, 9 tests green, DQ log written |
| 2 — Fair scorecard + ranking | 2026-09-29 16:08 | 16:15 | 0:07 | metrics/ranking, 15 tests green, 4 CSVs written |
| 3 — Lot alert + text rules + money | 2026-09-29 16:15 | 16:32 | 0:17 | lots/textrules/report, 22 tests green, full run 14s |
| 4 — Validation (sample + scoring) | 2026-09-29 16:32 | 16:47 | 0:15 | stratified sample of 180, score.py, 28 tests green, CLI smoke <1min |
| 5 — Report, memo, README, form, hygiene | 2026-09-29 16:47 | 17:14 | 0:27 | anonymised public outputs + --with-names, label_cli, memo/README/form/recording, fresh-venv proof, 28 tests green |
| 6 — Widen junk-IVR + consistency pass | 2026-09-29 17:14 | 17:23 | 0:09 | junk rule now flags <=3-char msgs (14→27), new test, 29 tests green, figures reconciled |
| 7 — AI-drafted labels + blind human check | 2026-09-30 | — | 0:22 | read 171 tickets blind, ai_label/ai_reason cols, verify_ids (40, seed 20260930), label_cli `--subset verify`, score.py all/human/agreement, 29 tests green |
| 8 — Rule v2 + held-out 60-ticket test | 2026-09-30 | — | 0:20 | froze v1, mined v2 (2 groups, aggregate-only, outside 180+60), make_test_set (60, seed 20261001, unread), score.py v1-vs-v2 + Wilson CIs + historical block, update_docs marked blocks, label_disagreements.md, hashes byte-identical, 35 tests green |

**Total so far: 2:11 — Opus build time only** (not a substitute for the human's honest hours). Final one-number hours: [USER TO FILL].

## Running notes
- 15:54 — Started. Row counts all reconcile with spec. `support-policy.pdf` is a real PDF, not a zip (spec D said zip). Policy constants taken from brief.
- 16:08 — Phase 1 done. tz fix verified (TK-240001=13min, TK-240002=17min), 2309 negatives→0 after +5h30m. Junk IVR: found 14 (ASR markers), not ~40. Duplicates: none. Money units: no rescale (ratios ~1.0 both). Counts reconcile: 11183 attendance + 567 open/pending = 11750. Fast profiling meant Phase 0+1 well under the 1:00 target.
- 16:47 — Phase 4 done. Stratified sample n=180 (fixed seed), no rule output leaked to the labelling file. Provisional score vs an independent heuristic draft: precision 92.7%, recall 90.5%, F1 0.92, error rate 3.9%; lot alert hits exactly PL2-2510/11/12 with 0 false alarms. Human `label` column left blank for real ground truth; score.py prefers it and flags PROVISIONAL otherwise. CLI smoke test runs the whole pipeline in <1 min. 28 tests green.
- 17:14 — Phase 5 done. Public outputs anonymised (agent_id+team only); names only via `--with-names` → gitignored `outputs/private/`. Added `.gitignore`, `label_cli.py`, status-tagged `results.md`, `report.html` validation line, `memo_to_priya.md` (466 words), `README.md`, `submission-form.md`, `recording_outline.md`. Clean-machine proof: fresh venv → `pip install -r requirements.txt` → `python -m vireo.run` (no PYTHONPATH) → 28 tests green.
- 2026-09-30 — Phase 8 done. Rule v2 for an honest before/after. Froze v1 (`flag_text_v1`,
  `charging_fault_text_v1`); v2 = v1 OR mined groups. Mined **aggregate-only** (no ticket text
  printed) from Pulse 2 tickets outside the 180 sample AND the 60 test set: only two groups earned
  a place — `dead_or_one_sided` (+6.3% lift) and `wiggle_or_press` (+3.4%); threw away no-green-light
  (0 hits), won't-hold-charge (negative lift) and Hinglish (0 hits) — all logged in
  `rule_v2_patterns.md`. Built the fresh 60-ticket test (`make_test_set.py`, seed 20261001, excludes
  the 180 + junk; 30/15/15) and did **not** read its rows. `score.py` now scores v1 vs v2 on the 60
  with Wilson 95% CIs + misclassified ids (states: pending/partial/complete), keeps the 180 sample as
  a clearly-marked historical block, and calls `update_docs.py` to fill the `<!-- VALIDATION -->`
  marked blocks in README/submission/report.html. Money + lot outputs **byte-identical** (hashes
  matched). `label_cli.py --file` added. `docs/label_disagreements.md` summarises the 10 disagreement
  KINDS. 35 tests green (added v1-frozen, v2-superset, v2-groups, precision-guard, hash-invariance).
  Held-out test is **pending human labels** — no v2 verdict claimed yet. No external API, Rs 0.
- 2026-09-30 — Phase 7 done. Opus hand-labelled the 171 not-yet-human rows **blind to the rule** (`ai_label`/`ai_reason`/`label_source`; 38 yes / 133 no); 9 human labels untouched. `verify_ids.txt` = 40 blind rows (seed 20260930); `label_cli.py --subset verify` hides `ai_label`. `score.py` now reports all-180 (P 100% / R 68.9% / F1 0.82 / err 7.8%), human-only (n=9), and human-vs-AI agreement; status **AI_DRAFT** until fully labelled. The 14 FNs are a genuine keyword-rule recall gap (battery-drain / wiggle / single-side), not label errors — rule stays a corroborating signal. Labels reproducible on a clean machine from committed text-free files (`_apply_ai_labels.py` + `verify_ids.txt`); `sample_to_label.csv` stays gitignored. `make_sample.main()` made non-destructive; sample-regen tests moved to tmp. 29 tests green. No external API, Rs 0.
