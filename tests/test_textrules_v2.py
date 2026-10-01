"""Tests for the frozen v1 rule and the mined v2 rule.

Guarantees: v1 behaviour is unchanged, v2 fires wherever v1 fires (superset), v2 catches the
mined failure kinds v1 misses, and v2 does not fire on clearly non-charging text (precision).
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vireo import textrules as tr  # noqa: E402


# --- v1 frozen behaviour (these exact verdicts must never change) ------------------------------
V1_CASES = [
    ("left bud not charging", "", True),          # explicit left-bud + charge
    ("the charging case won't charge", "", True),  # charge + case
    ("right earbud no charge at all", "", True),   # charge + bud
    ("great sound, very happy", "", False),        # no fault language
    ("bluetooth keeps disconnecting", "", False),  # pairing only, no charge word
    ("", "", False),                                # empty
    ("when will my order ship", "", False),        # delivery
]


def test_v1_frozen_behaviour():
    for msg, notes, expected in V1_CASES:
        assert tr.flag_text_v1(msg, notes) is expected, (msg, notes)
    # public alias still points at v1
    assert tr.flag_text is tr.flag_text_v1


# --- v2 is a superset of v1 (recall(v2) >= recall(v1) by construction) -------------------------
SUPERSET_PROBE = [m for m, _, _ in V1_CASES] + [
    "one is just decoration", "won't turn on unless I wiggle it",
    "right earbud is basically a paperweight", "package was damaged",
    "only works when I press it down hard", "please refund my coupon",
]


def test_v2_is_superset_of_v1():
    for msg in SUPERSET_PROBE:
        if tr.flag_text_v1(msg, ""):
            assert tr.flag_text_v2(msg, ""), f"v2 must fire wherever v1 fires: {msg!r}"


# --- v2 catches mined failure kinds that v1 misses ---------------------------------------------
V2_ONLY_POSITIVES = [
    "one of the buds is just a decoration now",   # dead_or_one_sided (no charge word)
    "the right earbud is basically a paperweight",  # dead_or_one_sided
    "left side stopped working entirely",           # dead_or_one_sided
    "it only works when I press it down in the case",  # wiggle_or_press
    "won't turn on unless I wiggle it around",      # wiggle_or_press
]


def test_v2_catches_mined_failure_kinds():
    for msg in V2_ONLY_POSITIVES:
        assert tr.flag_text_v2(msg, ""), f"v2 should catch: {msg!r}"
        assert not tr.flag_text_v1(msg, ""), f"expected v1 to miss (v2-only case): {msg!r}"


# --- v2 precision guard: must NOT fire on clearly non-charging text -----------------------------
V2_NEGATIVES = [
    "the package arrived damaged and the box was crushed",
    "please process my refund for the discount coupon",
    "when will my order be delivered to bangalore",
    "the sound quality is muddy and bass is weak",
    "how do I pair these with my iphone",
    "need a GST invoice for my purchase",
]


def test_v2_precision_guard():
    for msg in V2_NEGATIVES:
        assert not tr.flag_text_v2(msg, ""), f"v2 should NOT fire on: {msg!r}"


# --- each shipped v2 group is real and has a positive-example hit -------------------------------
def test_v2_groups_are_the_two_mined_ones():
    assert set(tr.V2_GROUPS) == {"dead_or_one_sided", "wiggle_or_press"}


# --- annotate: production column stays bound to frozen v1; both version columns exist -----------
def test_annotate_production_column_is_v1_and_junk_excluded():
    df = pd.DataFrame({
        "customer_message": ["one is just decoration", "left bud not charging", "[inaudible]"],
        "agent_notes": ["", "", ""],
        "is_junk_ivr": [False, False, True],
    })
    out = tr.annotate(df)
    for col in ("charging_fault_text", "charging_fault_text_v1", "charging_fault_text_v2"):
        assert col in out.columns
    # production == frozen v1
    assert out["charging_fault_text"].tolist() == out["charging_fault_text_v1"].tolist()
    # v2 catches the decoration row that v1 misses
    assert not out["charging_fault_text_v1"].iloc[0]
    assert out["charging_fault_text_v2"].iloc[0]
    # junk-IVR row is never flagged by either version
    assert not out["charging_fault_text_v1"].iloc[2]
    assert not out["charging_fault_text_v2"].iloc[2]
