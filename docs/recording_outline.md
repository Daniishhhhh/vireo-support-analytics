# Recording outline — 3 minutes, no slides (screen only)

Source: `docs/prompt_log.md`, `docs/decisions.md`. Show the terminal and `outputs/report.html`.
Goal: prompts used → what changed between versions → what was thrown away.

## 0:00–0:25 — The framing (the one prompt)
- Show `PROJECT_SPEC_v2.md` §0 and the single paste-ready brief in §10. Say: **one brief, no
  per-ticket prompting.** Point at the rule: *treat Section 1 numbers as hypotheses, not values to
  hard-code.* That decision drives everything.

## 0:25–1:10 — What changed between versions (recompute, don't copy)
- **Junk IVR:** spec estimate ~40 → recomputed **14** (ASR markers only). Thrown away: flagging
  Hinglish/typos as junk (would discard real complaints).
- **Money match:** spec used order_id only (~65%) → added a **conservative customer+sku fallback** →
  **94.5%** matched. Thrown away: an aggressive fallback that over-attributed to 46% (too loose).
- **Baseline:** first cut let bad lots pollute each other's baseline (~19%) → switched to a
  **healthy-lot baseline (~7%)** for the money math. Rupee number moved from spec's Rs 9.7 lakh to
  **Rs 12.5 lakh (floor)**.
- **Cost per unit:** Finance's Rs 2,500 → policy **Rs 1,820** (Rs 340 logistics), off by Rs 680.

## 1:10–2:00 — The fairness turn (the real test)
- Show `bottom_ten_naive.csv` → six **Tier 2** warranty agents at the bottom (the trap).
- Show `bottom_ten_adjusted.csv` → case-mix adjusted + shrunk + bootstrap CI → only **four Chat
  Frontline** agents are "clear evidence." `ranking_stability.csv`: they stay down across five
  methods, incl. excluding Pulse 2 tickets.
- **Two agents share a display name** (A3006 vs A3029) and land on opposite sides — proof we join on **agent_id**.

## 2:00–2:40 — Proof it works, honestly
- **The contamination trap and how I dodged it.** Opus read all 180 sample tickets, so they can't
  test a rule Opus then tuned. Show `validation/results.md`: block **(A)** is a *fresh 60-ticket
  held-out test* (`test_set_to_label.csv`, seed 20261001, none of the 180, junk excluded) labelled
  by a **human**, scoring **v1 (frozen) vs v2 (mined)** with Wilson 95% intervals; block **(B)** is
  the old 180 sample, clearly marked *"rule tuned after seeing these — NOT a test of v2."*
- **v2 was mined honestly.** `rule_v2_patterns.md`: only two groups earned a place by real bad-lot
  lift (dead/one-sided bud +6.3%, wiggle/press +3.4%); no-green-light, won't-hold-charge and
  Hinglish were **thrown away** (0 / negative lift). Mining was aggregate-only — no test ticket read.
- **The rule can't move the money.** v1↔v2 leaves `money_summary.md`/`lot_alerts.csv` byte-identical
  (hash test) — the rupee number comes from replacement orders, not text. Text is corroborating only.
- Demo `label_cli.py --file validation/test_set_to_label.csv` (rule/AI output hidden), then `score.py`.
- `pytest` → **35 green**, incl. v1-frozen, v2-superset, precision-guard, hash-invariance, <1-min smoke.

## 2:40–3:00 — Discarded / honest close
- Discarded: the `unzip support-policy.pdf` step (it is a real PDF) → constants from the brief.
- Public-repo hygiene: outputs show **agent_id + team only**; names only via `--with-names`
  (gitignored). Close on the memo headline: **it's one product from three lots, not the agents.**

## Things thrown away (mention at least two on camera)
- unzip-the-PDF step; aggressive order-matching fallback; polluted (all-lots) baseline;
  per-ticket LLM path (kept it deterministic, Rs 0).
