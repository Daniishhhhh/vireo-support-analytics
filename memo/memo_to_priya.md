# Memo — the CSAT slide

**To:** Priya (Support Lead)  **From:** Vendor eval build  **Re:** Why CSAT dipped, and what to do this week

## The short answer

The CSAT slide is **mostly one product, not the agents.** Almost all of the drop traces to the
**Pulse 2 earbuds** from **three production lots — PL2-2510, PL2-2511, PL2-2512.** Strip Pulse 2
out and monthly CSAT is flat at about **3.4–3.5** the whole period. With Pulse 2 in, overall CSAT
falls to roughly **2.96–3.22** across Dec 2025–Apr 2026. Those three lots are being replaced at
about **38–43%**, versus a healthy Pulse 2 baseline near **7%**.

## The money

Conservatively, the excess replacements on those lots are about **689 units ≈ Rs 12.5 lakh**, using
the **policy** replacement cost of **Rs 1,820 per unit** (unit cost 1,480 + Rs 340 logistics), *not*
the Rs 2,500 Finance has been using — that overstates each unit by Rs 680. This is a **floor**: it
counts only tickets we could tie to an order (about 94.5%). Units from these lots still inside
warranty could add roughly **Rs 8.8 lakh** if the fault rate holds.

## This week

1. **Ops/QC:** pull and inspect lots **2510/2511/2512**; hold or screen any remaining stock from them.
2. **Finance:** cost replacements at **Rs 1,820**, not Rs 2,500.
3. **Detection:** our lot alarm would have flagged these **~6 weeks** after they started shipping —
   worth wiring in so the next bad lot is caught in weeks, not quarters.

## The bottom ten (you asked for it — please use it carefully)

A raw "lowest CSAT" list points first at the **Tier 2 Escalations & Warranty** team. That is a
**queue effect**: they get the angriest cases by design, so ranking them against frontline teams is
unfair (and policy says don't). After adjusting for case mix and requiring the interval to clear
zero, only **four** Chat Frontline agents show up as **"clear evidence"** worth coaching. Everyone
else on the list is **"queue effect likely"** or **"insufficient evidence."** So: **coach the four,
don't spend the training budget on a raw list.** Note two different people share one display name
(agent_ids A3006 vs A3029) — we join on agent_id, and they land on opposite sides of this call,
which is exactly why.

## The festive-volume claim

Under "monthly mean CSAT of resolved/closed tickets with a score," the festive months (Oct–Nov
2025) sit at about **3.48–3.58** — *not* depressed. The real dip starts in **December** and is a
Pulse 2 pattern, not a seasonal-volume one.

## What we're unsure of

The validation error rate is **not yet final** — the sample labels are AI-drafted (read blind to
the rule) and a human is verifying a 40-ticket spot-check; the number firms up once that's done.
The rupee figure counts only matched orders (~35% of tickets have no order_id), and the root cause
is **"consistent with a manufacturing/QC fault — needs ops confirmation,"** not proven.
