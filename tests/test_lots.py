"""Phase 3 acceptance tests: defective-lot alert, money, text rules."""
import pytest

from vireo import lots, metrics, policy, textrules


@pytest.fixture(scope="module")
def lot(cleaned, raw):
    t = textrules.annotate(cleaned.tickets)
    t = metrics.add_derived(t, raw.products)
    return lots.build_lot_analysis(t, raw.orders, raw.products), t


def test_pl2_replacement_cost_is_1820():
    assert policy.replacement_cost_inr(1480) == 1820


def test_flags_the_three_bad_lots_without_hardcoding(lot):
    la, _ = lot
    flagged = set(la.alerts.loc[la.alerts["flagged"], "lot_key"])
    assert {"PL2-2510", "PL2-2511", "PL2-2512"} <= flagged


def test_no_false_alarms_on_other_lots(lot):
    la, _ = lot
    bad = {"PL2-2510", "PL2-2511", "PL2-2512"}
    others = la.alerts[la.alerts["flagged"] & ~la.alerts["lot_key"].isin(bad)]
    assert len(others) == 0


def test_matched_share_reported_and_reasonable(lot):
    la, _ = lot
    assert 0.5 < la.matched_share <= 1.0


def test_bad_lot_rate_far_above_baseline(lot):
    la, _ = lot
    bad = la.alerts[la.alerts["lot_key"] == "PL2-2510"].iloc[0]
    assert bad["replacement_rate"] > 3 * bad["healthy_baseline_rate"]


def test_text_rule_flags_left_bud_not_charging(lot):
    _, t = lot
    assert textrules.flag_text("left bud not charging", "") is True
    assert textrules.flag_text("great product, thanks", "") is False
    assert t["charging_fault_text"].sum() > 100


def test_wilson_lower_bounds():
    assert lots.wilson_lower(0, 0) == 0.0
    assert 0 < lots.wilson_lower(50, 100) < 0.5
