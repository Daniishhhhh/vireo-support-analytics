"""Static HTML report: no server, no CDN. Inline CSS + inline SVG charts.

Sections: (a) headline + rupee number, (b) monthly CSAT with/without Pulse 2,
(c) lot-alert table, (d) agent scorecard naive vs adjusted with caveat labels,
(e) data-quality summary.
"""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

CSS = """
body{font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;color:#1a1a2e;background:#fafafa}
.wrap{max-width:960px;margin:0 auto;padding:28px}
h1{font-size:26px;margin:0 0 4px} h2{font-size:19px;margin:28px 0 8px;border-bottom:2px solid #e0e0ea;padding-bottom:4px}
.headline{background:#0d3b66;color:#fff;padding:20px 24px;border-radius:10px}
.headline .num{font-size:30px;font-weight:700;color:#ffd166}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}
th,td{border:1px solid #dcdce6;padding:5px 8px;text-align:right}
th{background:#eef0f6;text-align:left} td:first-child,th:first-child{text-align:left}
.flag{background:#fde2e2;font-weight:600} .good{color:#0a7d3c}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:600}
.clear{background:#fddede;color:#a01919} .queue{background:#e2ecfb;color:#1a4c8b} .insuf{background:#eee;color:#555}
.muted{color:#666;font-size:13px} .legend{font-size:12px;margin:4px 0}
svg{background:#fff;border:1px solid #e0e0ea;border-radius:8px}
"""


def _esc(x) -> str:
    return html.escape(str(x))


def _read_validation(root: Path) -> str:
    """One-line validation summary parsed from validation/results.md (source of truth)."""
    f = root / "validation" / "results.md"
    if not f.exists():
        return ""
    import re
    m = re.search(r"<!-- VALIDATION status=(\w+) n_human=(\d+) precision=([\d.]+) recall=([\d.]+) "
                  r"f1=([\d.]+) error_rate=([\d.]+) n=(\d+) -->", f.read_text(encoding="utf-8"))
    if not m:
        return ""
    status, n_human, p, r, f1, err, n = m.groups()
    final = status == "FINAL"
    badge = "queue" if final else "clear"
    label = "FINAL — human-labelled" if final else f"AI-drafted, human-verified on {n_human} of {n}"
    prov = ("Human-labelled ground truth." if final else
            "Labels AI-drafted by Opus (blind to the rule) and being human-verified; "
            "Opus also built the rule, so these figures are not fully independent.")
    return (f'<p class="muted"><span class="tag {badge}">{label}</span> Validation on n={n} '
            f"(stratified sample): precision {float(p):.1%}, recall {float(r):.1%}, "
            f"F1 {float(f1):.2f}, error rate <b>{float(err):.1%}</b>. {prov}</p>")


def monthly_csat(tickets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Monthly mean CSAT overall and excluding Pulse 2 (VA-EB-PL2)."""
    v = tickets[tickets["csat_valid"]].copy()
    v["month"] = v["resolved_at_ist"].fillna(v["created_at"]).dt.to_period("M").astype(str)
    overall = v.groupby("month")["csat_score"].mean()
    ex = v[v["product_sku"] != "VA-EB-PL2"].groupby("month")["csat_score"].mean()
    pl2 = v[v["product_sku"] == "VA-EB-PL2"].groupby("month")["csat_score"].mean()
    return pd.DataFrame({"overall": overall, "ex_pulse2": ex, "pulse2_only": pl2}).reset_index()


def _svg_lines(df: pd.DataFrame, cols: dict[str, str], w=880, h=240) -> str:
    """Minimal multi-line SVG chart. cols maps column->colour."""
    pad = 40
    xs = list(range(len(df)))
    ymin, ymax = 2.0, 4.0
    def px(i): return pad + i * (w - 2 * pad) / max(len(df) - 1, 1)
    def py(v): return h - pad - (v - ymin) / (ymax - ymin) * (h - 2 * pad)
    parts = [f'<svg viewBox="0 0 {w} {h}" width="100%">']
    for gy in [2.5, 3.0, 3.5, 4.0]:
        parts.append(f'<line x1="{pad}" y1="{py(gy):.0f}" x2="{w-pad}" y2="{py(gy):.0f}" stroke="#eee"/>')
        parts.append(f'<text x="6" y="{py(gy)+4:.0f}" font-size="10" fill="#999">{gy:.1f}</text>')
    for col, colour in cols.items():
        pts = " ".join(f"{px(i):.0f},{py(v):.1f}" for i, v in enumerate(df[col]) if pd.notna(v))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2.5"/>')
    step = max(len(df) // 9, 1)
    for i in xs[::step]:
        parts.append(f'<text x="{px(i):.0f}" y="{h-14}" font-size="9" fill="#777" '
                     f'transform="rotate(35 {px(i):.0f} {h-14})">{_esc(df["month"].iloc[i])}</text>')
    parts.append("</svg>")
    return "".join(parts)


_LABEL_CLASS = {"clear evidence": "clear", "queue effect likely": "queue",
                "insufficient evidence": "insuf", "no CSAT data": "insuf"}


def _tag(label: str) -> str:
    return f'<span class="tag {_LABEL_CLASS.get(label, "insuf")}">{_esc(label)}</span>'


def _bottom_table(df: pd.DataFrame) -> str:
    head = ("<tr><th>Agent</th><th>Team</th><th>n</th><th>CSAT</th>"
            "<th>adj</th><th>95% CI</th><th>label</th></tr>")
    rows = []
    for _, r in df.iterrows():
        ci = f"[{r['adj_ci_lo']:.2f}, {r['adj_ci_hi']:.2f}]" if pd.notna(r["adj_ci_lo"]) else "-"
        rows.append(
            f"<tr><td>{_esc(r['display'])}</td><td>{_esc(r['team'])}</td>"
            f"<td>{int(r['csat_n'])}</td><td>{r['csat_mean']:.2f}</td>"
            f"<td>{r['adj_shrunk']:.2f}</td><td>{ci}</td><td>{_tag(r['label'])}</td></tr>"
        )
    return f"<table>{head}{''.join(rows)}</table>"


def _lot_table(alerts: pd.DataFrame) -> str:
    a = alerts[(alerts["orders"] >= 50) & (alerts["sku"] == "VA-EB-PL2")]
    head = ("<tr><th>Lot</th><th>Orders</th><th>Repl.</th><th>Rate</th>"
            "<th>Baseline</th><th>Flag</th><th>Detect</th></tr>")
    rows = []
    for _, r in a.iterrows():
        cls = ' class="flag"' if r["flagged"] else ""
        det = f"{int(r['weeks_to_detect'])} wks" if r["flagged"] and pd.notna(r.get("weeks_to_detect")) else ""
        rows.append(
            f"<tr{cls}><td>{_esc(r['lot_key'])}</td><td>{int(r['orders'])}</td>"
            f"<td>{int(r['replacements'])}</td><td>{r['replacement_rate']:.1%}</td>"
            f"<td>{r['healthy_baseline_rate']:.1%}</td>"
            f"<td>{'YES' if r['flagged'] else ''}</td><td>{det}</td></tr>"
        )
    return f"<table>{head}{''.join(rows)}</table>"


def write_report(path, tickets, raw, rank, lot) -> None:
    """Assemble the single static HTML report."""
    mc = monthly_csat(tickets, raw.products)
    chart = _svg_lines(mc, {"overall": "#0d3b66", "ex_pulse2": "#0a7d3c", "pulse2_only": "#d1495b"})
    excess_cost = lot.alerts.loc[lot.alerts["flagged"], "excess_cost_inr"].sum()
    excess_units = lot.alerts.loc[lot.alerts["flagged"], "excess_replacements"].sum()

    dq_rows = "".join(
        f"<tr><td>{_esc(r.rule)}</td><td>{r.count}</td></tr>" for r in _dq_entries(tickets)
    )
    validation_line = _read_validation(Path(path).resolve().parents[1])

    body = f"""
    <div class="headline">
      <div>Headline: the CSAT slide is one product, not the agents.</div>
      <div class="num">~Rs {excess_cost/1e5:.1f} lakh</div>
      <div>excess replacement cost (a floor) on Pulse 2 lots PL2-2510/2511/2512
      (~{excess_units:.0f} excess units at ~43% vs a ~7% baseline). Detected ~6 weeks
      after first shipment by the lot alert.</div>
    </div>

    <h2>Monthly CSAT: with vs without Pulse 2</h2>
    <div class="legend"><b style="color:#0d3b66">&#9644; overall</b> &nbsp;
      <b style="color:#0a7d3c">&#9644; excluding Pulse 2</b> &nbsp;
      <b style="color:#d1495b">&#9644; Pulse 2 only</b></div>
    {chart}
    <p class="muted">Excluding Pulse 2, CSAT is flat ~3.4-3.5. The dip is Pulse 2.</p>

    <h2>Defective-lot alert (Pulse 2)</h2>
    {_lot_table(lot.alerts)}
    <p class="muted">Flagged by a Wilson-lower-bound-vs-baseline rule (no lot names hard-coded).
    Order match rate {lot.matched_share:.1%}; figures are a floor. Replacement cost per unit
    = Rs 1,820 (policy), not Rs 2,500.</p>

    <h2>Agent scorecard: naive vs fair bottom ten</h2>
    <p class="muted"><b>Naive</b> (lowest raw CSAT) &mdash; a plain dashboard blames the Tier 2
    warranty team who get the angriest customers by design:</p>
    {_bottom_table(rank.naive)}
    <p class="muted"><b>Fair</b> (case-mix adjusted + shrunk, bootstrap CI) &mdash; coach only the
    "clear evidence" cases:</p>
    {_bottom_table(rank.adjusted)}

    <h2>Data-quality summary</h2>
    <table><tr><th>Rule</th><th>Rows</th></tr>{dq_rows}</table>
    <!-- VALIDATION:START -->
    {validation_line}
    <!-- VALIDATION:END -->
    <p class="muted">Full detail in outputs/data_quality_log.md. Every rank shows n; Tier 2 is
    never compared with Tier 1 on volume. Agent names are withheld from this public report
    (agent_id + team only).</p>
    """
    doc = (f"<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>Vireo Support Report</title><style>{CSS}</style></head>"
           f"<body><div class='wrap'><h1>Vireo Audio &mdash; Support Analytics</h1>"
           f"<p class='muted'>Static report. Generated by <code>python -m vireo.run</code>. "
           f"Deterministic; no model calls.</p>{body}</div></body></html>")
    Path(path).write_text(doc, encoding="utf-8")


def _dq_entries(tickets: pd.DataFrame):
    from types import SimpleNamespace as S
    return [
        S(rule="Legacy timezone fix (+5h30m)", count=int((tickets["source_system"] == "legacy_fd").sum())),
        S(rule="Open/pending excluded from CSAT & handle time", count=int(tickets["is_open"].sum())),
        S(rule="Junk IVR transcripts flagged", count=int(tickets["is_junk_ivr"].sum())),
        S(rule="Refund + replacement same ticket (policy breach)", count=int(tickets["refund_and_replacement"].sum())),
        S(rule="Valid CSAT (attendance + score)", count=int(tickets["csat_valid"].sum())),
    ]
