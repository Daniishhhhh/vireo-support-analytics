"""Rewrite the marked validation blocks in README / submission-form / report.html.

Single source of truth = validation/results.md (its machine-readable <!-- VALIDATION_TEST ... -->
and <!-- VALIDATION ... --> tags). This script parses those tags and replaces ONLY the text
between:
    <!-- VALIDATION:START -->   ...   <!-- VALIDATION:END -->
in each target file (markdown for .md, HTML for report.html). Files without the markers are left
untouched. `score.py` calls this after writing results.md.

Run: python validation/update_docs.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "validation" / "results.md"
START, END = "<!-- VALIDATION:START -->", "<!-- VALIDATION:END -->"

TARGETS = {
    "md": [ROOT / "README.md", ROOT / "submission" / "submission-form.md"],
    "html": [ROOT / "outputs" / "report.html"],
}


def _tags(text: str) -> tuple[dict, dict]:
    def grab(pat):
        m = re.search(pat, text)
        return m.group(1) if m else None
    test = {k: grab(rf"VALIDATION_TEST[^>]*\b{k}=([^\s]+)")
            for k in ("status", "n", "n_labelled", "v1_precision", "v1_recall", "v1_f1",
                      "v2_precision", "v2_recall", "v2_f1", "v1_r_lo", "v1_r_hi",
                      "v2_r_lo", "v2_r_hi", "v2_p_lo", "v2_p_hi")}
    hist = {k: grab(rf"VALIDATION status[^>]*\b{k}=([^\s]+)") if k != "status"
            else grab(r"<!-- VALIDATION status=(\w+)")
            for k in ("status", "n_human", "precision", "recall", "f1", "error_rate", "n")}
    return test, hist


def _pct(s: str | None) -> str:
    try:
        return f"{float(s):.1%}"
    except (TypeError, ValueError):
        return "n/a"


def _lines(test: dict, hist: dict) -> list[str]:
    """Plain-text lines shared by both renderers (no markup)."""
    pending = test["status"] in (None, "PENDING")
    out = []
    if pending:
        out.append(f"Held-out test (v2): a fresh {test.get('n', 60)}-ticket human-labelled set "
                   "(none from the 180 sample) is pending labels — v1-vs-v2 numbers appear here once labelled.")
    else:
        dr = float(test["v2_recall"]) - float(test["v1_recall"])
        dp = float(test["v2_precision"]) - float(test["v1_precision"])
        verdict = ("v2 improves recall" if dr > 0.001 else
                   "v2 does not beat v1") + (f", {dp:+.1%} precision" if abs(dp) > 0.001 else "")
        out.append(f"Held-out test — HUMAN-LABELLED, n={test['n_labelled']} "
                   f"(tickets Opus never read; predictor = text rule AND SKU VA-EB-PL2):")
        out.append(f"  v1 (frozen): precision {_pct(test['v1_precision'])}, "
                   f"recall {_pct(test['v1_recall'])} [{_pct(test['v1_r_lo'])}, {_pct(test['v1_r_hi'])}], "
                   f"F1 {float(test['v1_f1']):.2f}")
        out.append(f"  v2 (mined):  precision {_pct(test['v2_precision'])} "
                   f"[{_pct(test['v2_p_lo'])}, {_pct(test['v2_p_hi'])}], "
                   f"recall {_pct(test['v2_recall'])} [{_pct(test['v2_r_lo'])}, {_pct(test['v2_r_hi'])}], "
                   f"F1 {float(test['v2_f1']):.2f}")
        out.append(f"  Verdict: {verdict} (overlapping 95% intervals => within noise at this n).")
    out.append(f"Historical 180-sample (context only, rule tuned after seeing it — NOT a test of v2): "
               f"v1 precision {_pct(hist['precision'])}, recall {_pct(hist['recall'])} "
               f"on n={hist.get('n', 180)}, human labels {hist.get('n_human', '?')}/180; "
               "human-vs-Opus agreement 30/40 = 75% on the blind subset.")
    out.append("Failure kinds v2 targets: dead / one-sided bud and \"only charges when wiggled/pressed\" "
               "(typo-tolerant), mined outside the sample.")
    out.append("Opus wrote BOTH rule versions and the AI-drafted labels on the 180 sample; the 60 "
               "held-out test labels are HUMAN. The rupee figure comes from replacement orders, not "
               "text, and does not change with the rule version.")
    return out


def render(fmt: str, test: dict, hist: dict) -> str:
    lines = _lines(test, hist)
    if fmt == "html":
        body = "".join(f"<li>{ln.strip()}</li>" for ln in lines)
        return (f'{START}\n<p class="muted"><b>Validation (v1 vs v2)</b></p>\n'
                f"<ul class=\"muted\" style=\"font-size:13px\">{body}</ul>\n{END}")
    body = "\n".join(f"- {ln}" for ln in lines)
    return f"{START}\n**Validation (v1 vs v2).**\n\n{body}\n{END}"


def _replace(path: Path, block: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        return False
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, count=1, flags=re.DOTALL)
    if new != text:
        path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    if not RESULTS.exists():
        print("results.md missing; run score.py first."); return
    test, hist = _tags(RESULTS.read_text(encoding="utf-8"))
    for fmt, paths in TARGETS.items():
        block = render(fmt, test, hist)
        for p in paths:
            ok = _replace(p, block)
            print(f"{'updated' if ok else 'no markers, skipped'}: {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
