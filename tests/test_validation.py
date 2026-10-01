"""Phase 4 acceptance tests: validation sample, rule scoring, lot alert, and CLI smoke.

These import the validation helpers directly (they live outside src/, so add the path).
"""
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "validation"))

import make_sample  # noqa: E402
import score as scorer  # noqa: E402


@pytest.fixture(scope="module")
def scored():
    # Score the real, now-labelled sample (human labels + AI-drafted labels). Do NOT
    # regenerate it here — that would clobber the labels. Regeneration is tested in tmp dirs.
    return scorer.score()


def test_sample_is_stratified_and_sized(tmp_path):
    make_sample.main(out_dir=tmp_path)
    df = pd.read_csv(tmp_path / "sample_to_label.csv")
    assert 150 <= len(df) <= 200
    assert set(df["stratum"].unique()) == set(make_sample.STRATA_N)
    # NO rule output leaked into the labelling file (avoid biasing the human).
    assert "charging_fault_text" not in df.columns
    assert (df["label"].fillna("") == "").all()


def test_sample_is_deterministic(tmp_path):
    make_sample.main(out_dir=tmp_path / "a")
    a = pd.read_csv(tmp_path / "a" / "sample_to_label.csv")["ticket_id"].tolist()
    make_sample.main(out_dir=tmp_path / "b")
    b = pd.read_csv(tmp_path / "b" / "sample_to_label.csv")["ticket_id"].tolist()
    assert a == b


def test_rule_scores_are_reasonable(scored):
    m = scored["metrics"]
    assert m["n"] >= 150
    # Scored against best-available truth on the 180 sample (now mostly human labels). Precision
    # stays high; recall is a DOCUMENTED gap — the human labels "any Pulse-2 fault" (incl. pairing/
    # app/seating), while the charging-keyword rule only fires on charging/power language. That
    # scope difference (see docs/label_disagreements.md) — not a bug — pulls recall down. The rule
    # is a corroborating signal, not a general fault classifier; the money never uses it.
    assert m["precision"] >= 0.7
    assert m["recall"] >= 0.4
    assert m["error_rate"] <= 0.35


def test_lot_alert_hits_bad_lots_no_false_alarms(scored):
    lc = scored["lot_check"]
    assert lc["hits"] == ["PL2-2510", "PL2-2511", "PL2-2512"]
    assert lc["false_alarms"] == []
    assert lc["missed"] == []


def test_results_md_written(scored):
    scorer.write_results(scored)
    text = (ROOT / "validation" / "results.md").read_text(encoding="utf-8")
    low = text.lower()
    assert "error rate" in low
    assert "confusion" in low
    # both machine-readable tags and both blocks (held-out test + historical) are present
    assert "<!-- validation_test" in low and "<!-- validation status=" in low
    assert "held-out test" in low and "not a test of v2" in low


def test_cli_smoke_under_a_minute(tmp_path):
    """`python -m vireo.run` regenerates all outputs in well under a minute."""
    start = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "vireo.run", "--data", "data/raw",
         "--out", str(tmp_path / "out"), "--processed", str(tmp_path / "proc")],
        cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": "src"},
        capture_output=True, text=True, timeout=90,
    )
    assert proc.returncode == 0, proc.stderr
    assert time.time() - start < 60
    assert (tmp_path / "out" / "report.html").exists()
    assert (tmp_path / "out" / "lot_alerts.csv").exists()

    # Money + lot outputs must be byte-identical to the committed ones: they never read the text
    # rule, so introducing v2 cannot move them. This is the hash-invariance guarantee.
    for name in ("money_summary.md", "lot_alerts.csv",
                 "bottom_ten_naive.csv", "bottom_ten_adjusted.csv"):
        fresh = (tmp_path / "out" / name).read_bytes()
        committed = (ROOT / "outputs" / name).read_bytes()
        assert fresh == committed, f"{name} changed — the money/lot path must be rule-agnostic"
