# Prompt Log

Prompts used while building, what changed between versions, and what was discarded. This backs the 3-minute screen recording. Honest account.

## Meta

* The whole build was driven by one large paste-ready brief (`PROJECT_SPEC_v2.md` §10 plus the delivery brief). No prompt was sent per ticket. **Zero paid model calls in the default code path** — all free-text handling is deterministic (see `src/vireo/textrules.py`).

## Attempts & changes

* **Policy unzip.** First plan: `unzip support-policy.pdf` → failed, it is a real PDF. Discarded the unzip step; encoded policy constants from the brief into `policy.py` instead. Logged in `decisions.md`.

## Prompt sequence (Claude chat → Claude Opus 4.8 in VS Code)

The build was driven by eight prompts across two tools (listed below).

1. **Analysis prompt (chat, before the real brief).** Asked Claude to turn the data pack into an implementation spec. Produced a 15-hour, six-page-dashboard spec (`v1`).
   **Changed:** the real brief arrived with a 5-hour cap, so v1 was thrown away.

2. **Spec v2 (chat).** Re-scoped to a small CLI + static report, built around the finding that the CSAT dip is Pulse 2 lots PL2-2510/2511/2512, not agents.

3. **Opus build prompt, 5 phases.** Clean → scorecard → lot alert → validation → docs. Rules: join on `agent_id`, legacy +5:30 timezone fix, no paid model calls, stop after each phase.

4. **Phase-5 prompt.** Added an audit gate, PROVISIONAL tags on validation, anonymised public outputs (`agent_id` only), report/memo/README/form.
   **Changed:** the first validation figure (3.9% error) was scored against Opus's own heuristic, so I stopped treating it as real.

5. **Junk-IVR + consistency prompt.** Widened the junk rule from 14 to 27 and checked every figure in memo/report/form against source files.

6. **Label-drafting prompt.** Opus drafted 171 validation labels blind to the rule; I labelled 9, then 40 blind. Agreement was only 75%, so the AI labels were not trustworthy.

7. **Rule v2 prompt.** Mined new patterns outside the sample; tested v1 vs v2 on a fresh 60-ticket set that I labelled: recall 54.1% → 62.2%, error 28.3% → 23.3%, within noise.

8. **Names + form prompt.** Removed agent names from public files and added a test that fails if one appears.

## Thrown away

* The 15-hour spec and six-page dashboard; training-budget split; Diwali top-five.
* The `unzip support-policy.pdf` step (it is a real PDF on this machine).
* The 3.9% / 7.8% provisional error rates (circular, scored against Opus's own labels).
* The "battery drain" and "no green light" keyword patterns (negative lift / no hits outside the sample).
* Using the AI-labelled 180 tickets as a test set for v2.
* Per-ticket LLM calls (Rs 5 × 2,817 = Rs 14,085/month).

## Optional LLM path (validation labelling only)

See `docs/ai_usage_log.md`. Any LLM use is offline, one-off, off by default, on the ~150–200 ticket validation sample only, and human-reviewed. Prompts used there are recorded in that file.
