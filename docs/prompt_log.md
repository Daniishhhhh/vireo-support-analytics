# Prompt Log

Prompts used while building, what changed between versions, what was discarded. This backs
the 3-minute screen recording. Honest account.

## Meta

- The whole build was driven by one large paste-ready brief (`PROJECT_SPEC_v2.md` §10 plus
  the delivery brief). No prompt was sent per ticket. **Zero paid model calls in the default
  code path** — all free-text handling is deterministic (see `src/vireo/textrules.py`).

## Attempts & changes

- **Policy unzip.** First plan: `unzip support-policy.pdf` → failed, it is a real PDF. Discarded
  the unzip step; encoded policy constants from the brief into `policy.py` instead. Logged in
  `decisions.md`.

<!-- APPEND-PROMPT -->

## Optional LLM path (validation labelling only)

See `docs/ai_usage_log.md`. Any LLM use is offline, one-off, off by default, on the ~150–200
ticket validation sample only, and human-reviewed. Prompts used there are recorded in that file.
