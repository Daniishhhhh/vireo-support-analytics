# Human-vs-Opus label disagreements (blind-check subset)

On the 40-ticket blind-verification subset (human labelled without seeing the AI draft), human
and Opus labels agreed on **30/40 = 75%**. The 10 disagreements are summarised here **by kind**,
counts only — this is a description of *where* two labellers differ, **not** an input to any rule
tuning. (The rule was never changed to chase these; see `docs/decisions.md`.)

Direction: **9 of 10** are `human=yes / Opus=no` — Opus applied a strict "Pulse-2 **charging/power
hardware** fault" definition, while the human marked a genuine-fault YES more broadly. Only **1**
is `human=no / Opus=yes`.

| kind of ticket | count | direction | what differed |
|---|---:|---|---|
| pairing / bluetooth / connectivity | 4 | human=yes, Opus=no | Opus scored "pairing/connection drops" as **not a charging fault**; the human counted it as a fault. |
| app / firmware / loading screen | 2 | human=yes, Opus=no | Opus treated app/update problems as software, not a hardware charging fault; the human marked them YES. |
| pod won't seat / "stays flat" in case | 1 | human=yes, Opus=no | Borderline seating issue Opus called "no charge fault"; the human read it as a charging-contact fault. |
| left bud at 0% in case (mis-attributed SKU) | 1 | human=yes, Opus=no | A real left-bud-not-charging ticket Opus wrongly read as another product; the human caught the fault. |
| non-Pulse-2 product | 1 | human=yes, Opus=no | A non-Pulse-2 item where Opus said "another product → no"; the human still marked YES (scope difference). |
| ambiguous left-bud mention | 1 | human=no, Opus=yes | The one Opus over-call: Opus inferred a charging fault from a left-bud mention the human judged not a fault. |

**Reading.** The gap is mostly a **definition-scope** difference, not random noise: Opus labelled
"charging/power hardware fault only", the human labelled the broader "is this a real Pulse-2 fault".
That same scope difference is why the human-only recall of the *charging-text* rule looks low — the
human marks pairing/app/seating faults YES, which a charging-keyword rule is not meant to fire on.
The rule stays a **corroborating** signal for the lot alert (costed from replacement orders, not
text); it is not a general fault classifier. No labels or patterns were adjusted after seeing this.
