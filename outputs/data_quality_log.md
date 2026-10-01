# Data Quality Log

Raw tickets loaded: **11750**. Every rule below is a flag/fix/exclusion with its row count and example ids. Nothing is silently dropped; flags let the metric layer include/exclude explicitly.

## 1. Legacy timezone fix: +5h30m on legacy_fd resolved_at (UTC→IST)
- **Rows affected:** 3374
- **Examples:** TK-240001 (13 min), TK-240002 (17 min)
- Verified against the two anchor tickets. Helpdesk timestamps unchanged.

## 2. Open/pending tickets excluded from handle time and CSAT (blank resolved_at)
- **Rows affected:** 567
- **Examples:** TK-240031, TK-240035, TK-240040
- 249 of these still carry a CSAT score; excluded (not attendance).

## 3. Junk IVR transcripts flagged (ASR markers [inaudible]/[crosstalk]/[line dropped] or message <=3 chars)
- **Rows affected:** 27
- **Examples:** TK-240296, TK-240351, TK-240456
- Sameer estimated ~40; found 27 failed transcripts (14 with ASR-failure markers + 13 with <=3-char messages like '...'). The remaining gap to ~40 is voice messages with typos/Hinglish but real intent, which are NOT junk. Excluded from text analysis only; not counted against agents.

## 4. Re-import duplicate check (same customer+sku, <=6h apart, across sources)
- **Rows affected:** 0
- NONE FOUND. Also checked exact-content and exact created_at across sources: 0. No de-duplication applied.

## 5. Legacy money-unit check (refund scale legacy vs helpdesk)
- **Rows affected:** 0
- **Examples:** legacy median 2250, helpdesk median 2499
- Distributions overlap (medians ~2,250 vs ~2,500; refund/order_value ratio ~1.0 in both). NO rescale applied. Legacy values treated as INR.

## 6. Refund + replacement on the same ticket (policy §5 prohibits — escalate)
- **Rows affected:** 6
- **Examples:** TK-240833, TK-244004, TK-245019
- Reported as a by-product finding; not modified.

## 7. Valid CSAT = attendance (resolved/closed) with a score present
- **Rows affected:** 4947
- 5196 scores exist; blanks excluded (never zero).
