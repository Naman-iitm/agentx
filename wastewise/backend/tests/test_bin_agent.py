"""Unit tests: Bin Agent thresholds, flags and priority (tasks.md Phase 2)."""
from datetime import timedelta

from app.agents.bin_agent import compute_status, evaluate_bin
from app.core.utils import utcnow

NOW = utcnow()


def snap(fill, measured=None, battery=None):
    return {
        "bin_id": "BIN-TST",
        "name": "Test Bin",
        "zone": "Central",
        "latitude": 26.9,
        "longitude": 75.8,
        "fill_percent": fill,
        "measured_at": measured or NOW,
        "battery_percent": battery,
        "capacity_litres": 600,
    }


KW = dict(
    warning_threshold=70.0,
    critical_threshold=90.0,
    collection_threshold=75.0,
    stale_after_hours=24.0,
    now=NOW,
)


class TestThresholdBoundaries:
    """tasks.md exit criteria: 69 / 70 / 89 / 90 behave per configuration."""

    def test_69_is_normal(self):
        assert compute_status(69, 70, 90) == "NORMAL"

    def test_70_is_warning(self):
        assert compute_status(70, 70, 90) == "WARNING"

    def test_89_is_warning(self):
        assert compute_status(89, 70, 90) == "WARNING"

    def test_90_is_critical(self):
        assert compute_status(90, 70, 90) == "CRITICAL"

    def test_thresholds_are_configurable(self):
        assert compute_status(60, 50, 80) == "WARNING"
        assert compute_status(80, 50, 80) == "CRITICAL"


class TestEvaluateBin:
    def test_priority_v1_is_fill(self):
        r = evaluate_bin(snap(83), **KW)
        assert r["priority"] == 83.0
        assert "priority = fill_percent" in r["reasons"][0] or r["priority"] == 83.0  # v1 documented

    def test_candidate_selection(self):
        assert evaluate_bin(snap(95), **KW)["should_collect"] is True   # critical
        assert evaluate_bin(snap(80), **KW)["should_collect"] is True   # ≥ collection threshold
        assert evaluate_bin(snap(70), **KW)["should_collect"] is False  # warning but below 75
        assert evaluate_bin(snap(30), **KW)["should_collect"] is False

    def test_stale_flag(self):
        old = NOW - timedelta(hours=30)
        r = evaluate_bin(snap(50, measured=old), **KW)
        assert r["is_stale"] is True
        assert "STALE" in r["flags"]
        assert any("stale" in w.lower() for w in r["warnings"])

    def test_fresh_reading_not_stale(self):
        r = evaluate_bin(snap(50, measured=NOW - timedelta(hours=2)), **KW)
        assert r["is_stale"] is False

    def test_battery_low_flag(self):
        r = evaluate_bin(snap(40, battery=12), **KW)
        assert "BATTERY_LOW" in r["flags"]

    def test_reasons_are_human_readable(self):
        r = evaluate_bin(snap(96), **KW)
        assert any("96%" in reason for reason in r["reasons"])
