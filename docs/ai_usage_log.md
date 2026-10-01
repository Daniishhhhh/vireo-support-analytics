# AI Usage Log

Honest account of AI use, tokens, and cost. The evaluator asks for this specifically.

## Default path: ZERO paid model calls

The shipped tool (`python -m vireo.run`) makes **no LLM calls**. All free-text handling
(defect-language flags, junk-IVR detection) is deterministic keyword/regex scoring in
`src/vireo/textrules.py`. Cost per run = **Rs 0**.

Rationale: Finance (Arjun) rejected "Rs 5 a pop across twelve thousand tickets". At
~2,817 tickets/month a per-ticket LLM call would cost ~2,817 × Rs 5 ≈ **Rs 14,085/month**.
The rules cost Rs 0/month.

## Validation labels — how ground truth is built

Three label sources, in priority order (`validation/score.py`):

1. **Human `label`** in `validation/sample_to_label.csv` — the real ground truth; overrides all else.
2. **`ai_label` — drafted by Opus (this coding assistant), blind to the rule.** Opus read each of
   the 171 not-yet-human-labelled tickets (customer_message + agent_notes + product_sku only) and
   wrote a yes/no in `ai_label` plus a short `ai_reason`. It did **not** run `textrules.py` /
   `charging_fault_text`, did **not** open `sample_draft_labels.csv` or `results.md`, and used **no
   regex/script** to decide — the transcription script `validation/_apply_ai_labels.py` only writes
   the judgements down. **Caveat: Opus also built the rule, so these labels are NOT fully
   independent** — treat all-180 figures as indicative and lean on the human-verified block.
3. **Regex heuristic** (`make_sample._GOLD`, `sample_draft_labels.csv`) — last-resort fallback only
   when a row has neither a human nor an AI label (e.g. a freshly regenerated sample).

### Blind human verification (independence check)
`validation/verify_ids.txt` holds **40 tickets** drawn at random from the 171 AI-drafted rows
(fixed seed **20260930**, none among the 9 existing human rows). The human labels those 40 with
`python validation/label_cli.py --subset verify`, which **hides `ai_label`** and writes to the
human `label` column. `score.py` then reports **human-vs-AI agreement** on exactly those rows. The
agreement % is **produced by `score.py`, not invented here**.

### Rule v2 and its held-out test (independence, done right)
Opus built **both** rule versions, so the 180 sample (which Opus read) cannot fairly test the tuned
v2. Two safeguards:
- **v2 was mined aggregate-only.** `validation/mine_v2.py` computes phrase-frequency counts over
  Pulse 2 tickets **outside** the 180 sample **and** the 60-ticket test; it prints/writes only
  aggregate numbers, never an individual ticket's text. So no test ticket was read while building v2.
- **The 60-ticket held-out test is labelled by a HUMAN, not Opus.** `make_test_set.py` writes
  `test_set_to_label.csv` (no rule/AI columns); Opus did not read, print or label any of its rows.
  `score.py` scores v1 vs v2 on the same 60 with Wilson 95% intervals. Until those labels exist the
  block is tagged **PENDING** and no v2 verdict is claimed.

### Cost
No external API was called. Labels were produced by the coding assistant (Opus) in-session; the
shipped tool still makes **zero paid model calls**. Marginal cost = **Rs 0** beyond the existing
coding-assistant subscription (this includes the v2 mining and the AI-drafted sample labels).

## Optional offline path (per-ticket LLM labelling in production) — OFF by default, not used

| Item | Value |
|---|---|
| Used in the shipped tool? | No — production text handling is deterministic (Rs 0/run) |
| Tool / model | Opus (coding assistant), one-off, for the 180-row validation sample only |
| What for | Draft "Pulse 2 charging fault yes/no" labels for a human to verify. Ground truth = human labels. |
| External API tokens / cost | None — no external API call; Rs 0 marginal |
| One-off or recurring | One-off, offline, on a deduplicated 180-row sample only |

Prompt-equivalent applied while reading (no API call made):
> Does this ticket describe a **Pulse 2 (VA-EB-PL2)** charging/power hardware fault — bud not
> charging, dead bud, works only when wiggled in the case, case not charging, battery won't hold
> charge? Any other product, damage, delivery, payment, app/pairing/sound-only, or status query = no.
