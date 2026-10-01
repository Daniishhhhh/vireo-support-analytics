"""Phase 1 acceptance tests: load, timezone fix, integrity, flags."""
import pandas as pd

from vireo import policy


def test_row_counts(raw):
    assert len(raw.tickets) == 11750
    assert len(raw.orders) == 15500
    assert len(raw.customers) == 9500
    assert len(raw.agents) == 44
    assert len(raw.products) == 14


def test_legacy_tz_fix_anchor_tickets(cleaned):
    t = cleaned.tickets.set_index("ticket_id")
    assert t.loc["TK-240001", "handle_time_min"] == 13
    assert t.loc["TK-240002", "handle_time_min"] == 17


def test_no_negative_handle_times(cleaned):
    t = cleaned.tickets
    resolved = t["resolved_at_ist"].notna() & t["first_response_at"].notna()
    assert (t.loc[resolved, "handle_time_min"] >= 0).all()


def test_shared_display_name_agents_stay_separate(raw):
    # The real roster has a display name shared by two different agent_ids. Joining on name
    # would merge them; we join on agent_id. Detect the pair generically (no real name in source).
    counts = raw.agents["name"].value_counts()
    shared = counts[counts > 1].index
    assert len(shared) >= 1, "expected at least one display name shared by two agents"
    for nm in shared:
        ids = set(raw.agents.loc[raw.agents["name"] == nm, "agent_id"])
        assert len(ids) >= 2  # same display name, distinct agent_ids
    # the known pair is keyed by agent_id, not by name
    assert {"A3006", "A3029"}.issubset(set(raw.agents["agent_id"]))


def test_blank_csat_excluded_never_zero(cleaned):
    t = cleaned.tickets
    # valid CSAT never includes a blank, and no score was coerced to zero
    assert t.loc[t["csat_valid"], "csat_score"].notna().all()
    assert (t["csat_score"].dropna() >= 1).all()


def test_open_pending_excluded_from_handle_time(cleaned):
    t = cleaned.tickets
    assert t.loc[t["is_open"], "handle_time_min"].isna().all()
    assert t["is_open"].sum() == 567


def test_refund_and_replacement_flagged(cleaned):
    assert cleaned.tickets["refund_and_replacement"].sum() == 6


def test_ticket_id_unique(cleaned):
    assert cleaned.tickets["ticket_id"].is_unique


def test_all_agents_in_roster(raw, cleaned):
    assert cleaned.tickets["agent_id"].isin(raw.agents["agent_id"]).all()


def test_junk_ivr_flags_markers_and_short_messages(cleaned):
    t = cleaned.tickets
    # 14 ASR-marker transcripts + 13 messages of <=3 chars = 27 (not forced to Sameer's ~40).
    assert t["is_junk_ivr"].sum() == 27
    msg = t["customer_message"].fillna("").str.strip()
    # every <=3-char message is flagged junk
    assert t.loc[msg.str.len() <= 3, "is_junk_ivr"].all()
    # a real, longer complaint is not flagged
    assert not t.loc[msg.str.len() > 10, "is_junk_ivr"].all()
