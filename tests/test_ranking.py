"""Phase 2 acceptance tests: scorecard + fair ranking."""
import pytest

from vireo import metrics, ranking


@pytest.fixture(scope="module")
def scored(cleaned, raw):
    t = metrics.add_derived(cleaned.tickets, raw.products)
    sc = metrics.agent_scorecard(t, raw.agents)
    rk = ranking.build_rankings(t, raw.agents, sc)
    return t, sc, rk


def test_all_44_agents_once(scored):
    _, sc, _ = scored
    assert len(sc) == 44
    assert sc["agent_id"].is_unique


def test_bottom_ten_have_ten_rows(scored):
    _, _, rk = scored
    assert len(rk.naive) == 10
    assert len(rk.adjusted) == 10


def test_shared_name_agents_separate_in_scorecard(scored):
    _, sc, _ = scored
    # A display name shared by two agent_ids must not be collapsed in the scorecard.
    counts = sc["name"].value_counts()
    shared = counts[counts > 1].index
    assert len(shared) >= 1
    for nm in shared:
        assert sc[sc["name"] == nm]["agent_id"].nunique() >= 2
    # the known pair (referenced by agent_id, not name) gets distinct scores → separate agents
    pair = sc[sc["agent_id"].isin(["A3006", "A3029"])]
    assert pair["agent_id"].nunique() == 2
    assert pair["csat_mean"].nunique() == 2


def test_tier2_labelled_queue_effect(scored):
    _, _, rk = scored
    t2 = rk.scorecard[rk.scorecard["is_tier2"]]
    assert (t2["label"] == "queue effect likely").all()


def test_naive_surfaces_tier2_but_adjusted_does_not_dominate(scored):
    _, _, rk = scored
    # the trap: naive bottom ten is heavy with Tier 2
    assert rk.naive["tier"].eq(2).sum() >= 5
    # fair method promotes them out: adjusted has fewer Tier 2
    assert rk.adjusted["tier"].eq(2).sum() < rk.naive["tier"].eq(2).sum()


def test_deterministic_across_reruns(scored, raw):
    t, sc, rk1 = scored
    rk2 = ranking.build_rankings(t, raw.agents, sc)
    assert list(rk1.adjusted["agent_id"]) == list(rk2.adjusted["agent_id"])
    assert rk1.scorecard["adj_score"].round(6).equals(rk2.scorecard["adj_score"].round(6))
