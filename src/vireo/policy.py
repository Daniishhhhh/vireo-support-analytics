"""Policy constants from support-policy v3.2 (see brief POLICY CONSTANTS).

All monetary values in INR. The source `support-policy.pdf` is a real 2-page PDF (not a zip
as the brief guessed); these constants are transcribed from the brief's summary and kept in
one place so every calculation references the policy, not a magic number.
"""
from __future__ import annotations

# First-response targets (minutes), measured from ticket creation. Breach = later than target.
FIRST_RESPONSE_TARGET_MIN: dict[str, int] = {
    "chat": 15,
    "voice": 120,   # 2 hours (voice callback)
    "social": 240,  # 4 hours
    "email": 480,    # 8 hours
}

# Per-event costs (INR)
BREACH_CREDIT_INR = 350       # per breached ticket
TRANSFER_COST_INR = 305       # per transfer
REPLACEMENT_LOGISTICS_INR = 340  # added to unit cost for a replacement
AGENT_HOURLY_INR = 165
AGENT_SHIFT_HOURS = 8

# Contact cost by channel (INR)
CONTACT_COST_INR: dict[str, int] = {
    "chat": 210,
    "email": 260,
    "voice": 520,
    "social": 240,
}
CONTACT_COST_BLENDED_INR = 290

# Legacy timezone fix: legacy_fd resolved_at is UTC, add 5h30m to get IST.
LEGACY_SOURCE = "legacy_fd"
HELPDESK_SOURCE = "helpdesk"
LEGACY_TZ_OFFSET_HOURS = 5.5

# Helpdesk went live on this date; earlier tickets are legacy_fd.
HELPDESK_GO_LIVE = "2025-09-14"

# Shifts (IST), [start_hour, end_hour)
SHIFTS = {
    "Morning": (6, 14),
    "Day": (14, 22),
    "Night": (22, 6),
}

# CSAT / attendance
ATTENDANCE_STATUSES = {"resolved", "closed"}  # surveyed; count as attendance
# blank CSAT = no response: exclude, never zero.

# Tier 2 team: measured in days-to-resolve, never compared with Tier 1 on volume.
TIER2_TEAM = "Escalations & Warranty"

# Refund reason codes (policy §5)
REFUND_REASON_CODES = {
    "GW-OTHER", "DOA-REPL", "LOST-TRANSIT", "DUP-PAYMENT",
    "CANCEL", "PRICE-ADJ", "RETURN-QC-OK", "WTY-BUYBACK",
}

# Expected raw row counts (assert on load; in = out + logged drops).
EXPECTED_ROW_COUNTS = {
    "tickets": 11750,
    "orders": 15500,
    "customers": 9500,
    "agents": 44,
    "products": 14,
}


def replacement_cost_inr(unit_cost_inr: float) -> float:
    """Policy §5 replacement cost = unit cost + Rs 340 logistics."""
    return float(unit_cost_inr) + REPLACEMENT_LOGISTICS_INR
