"""Privacy guard: no real agent full name may appear in a committed/public file.

The repo and Drive folder are public. Agent performance is shown as agent_id + team only; real
names live solely in data/raw/agents.csv (gitignored) and, at runtime, in the --with-names private
outputs. This test reads the roster's `name` column and fails if any full name leaks into a public
deliverable. Skipped when data/raw is absent (e.g. a clean checkout without the data pack).
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "data" / "raw" / "agents.csv"

# Paths never scanned: the data pack, gitignored label files, private outputs, tooling, and the
# externally-provided client brief (an input artifact the user places, not a deliverable we author).
EXCLUDE_PARTS = {".venv", "__pycache__", ".git", ".pytest_cache"}
EXCLUDE_REL = {
    "data/raw", "data/processed", "outputs/private",
    "validation/sample_to_label.csv", "validation/sample_to_label.backup.csv",
    "validation/test_set_to_label.csv", "PROJECT_SPEC_v2.md",
}
SCAN_EXTS = {".md", ".py", ".html", ".csv", ".txt"}


def _is_public(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    if any(part in EXCLUDE_PARTS for part in p.parts):
        return False
    return not any(rel == e or rel.startswith(e + "/") for e in EXCLUDE_REL)


def _public_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in SCAN_EXTS and _is_public(p):
            yield p


def test_no_agent_full_name_in_public_files():
    if not AGENTS.exists():
        pytest.skip("data/raw/agents.csv absent — cannot check names on this checkout")
    names = sorted({n.strip() for n in pd.read_csv(AGENTS, dtype=str)["name"].dropna()
                    if len(n.split()) >= 2})
    assert names, "expected multi-word agent names in the roster"

    hits: list[str] = []
    for p in _public_files():
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name in names:
            if name in text:
                hits.append(f"{p.relative_to(ROOT).as_posix()} contains agent name {name!r}")
    assert not hits, "Real agent names leaked into public files:\n" + "\n".join(hits)
